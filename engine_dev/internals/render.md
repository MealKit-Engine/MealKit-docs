# Render

This page explains how the renderer works inside: the thin graphics layer (RHI) under it, how it starts, what one frame does, how instances reach the GPU, how the shaders light the scene, and how the 2D UI pass, screenshots and statistics work.
The frame budget and the profiler are in {doc}`../../manual/performance`. The code is in {engine}`engine/src/mealkit/render`, {engine}`engine/src/mealkit/rhi` and the shaders in {engine}`engine/shaders`.

`rhi` and then `render` come after `scene` in the folder order of {engine}`docs/CODING_MODEL.md` ("엔진 폴더 사이 의존").
`asset`, `debug` and `ui` come after them and give the renderer meshes, ImGui draw data and UI rectangles.

## Files

| File | Holds |
|---|---|
| {engine}`engine/src/mealkit/rhi/Rhi.h` | The RHI: `Device`, `CommandList`, buffer, texture and pipeline handles, GPU information and the debug UI drawing functions. No graphics API type appears in it. |
| {engine}`engine/src/mealkit/rhi/dx12/Dx12Device.cpp` | The Direct3D 12 backend. Only files in `rhi/<api>/` include graphics API headers. |
| {engine}`engine/src/mealkit/rhi/dx12/Dx12ImGui.cpp` | Draws Dear ImGui with its stock DX12 backend (debug UI builds only). |
| {engine}`engine/src/mealkit/rhi/vulkan/VkDevice.cpp` | The Vulkan 1.3 backend (`build.bat Vulkan`, `VulkanEditor`). |
| {engine}`engine/src/mealkit/rhi/vulkan/VkImGui.cpp` | Draws Dear ImGui with its stock Vulkan backend. |
| {engine}`engine/src/mealkit/rhi/vulkan/VkLibs.cpp` | The implementations of volk (Vulkan loader) and the Vulkan Memory Allocator. |
| {engine}`engine/src/mealkit/render/Renderer.h` | `Renderer`, the per-frame values (`FrameParams`), the 48-byte `InstanceData`, the 112-byte `UiQuad` and `RenderStats`. |
| {engine}`engine/src/mealkit/render/Renderer.cpp` | The forward renderer, written only against the RHI. |
| {engine}`engine/src/mealkit/render/DrawList.h` | Collects instances per mesh for one frame. |
| {engine}`engine/src/mealkit/render/Mesh.h` | The 28-byte `Vertex`, `MeshData` and the unit box. |
| {engine}`engine/shaders/Bindless.hlsli` | The binding layout that every shader shares. |
| {engine}`engine/shaders/Forward.hlsl` | The 3D shader: instance transform, lighting and fog. |
| {engine}`engine/shaders/Ui.hlsl` | The 2D UI shader: rounded boxes, gradients, shadows, images and SDF text. |

The shaders are compiled at build time by DXC into header files with byte arrays (`g_ForwardVS.h`, `g_UiPS.h`, ...), see {engine}`engine/CMakeLists.txt`.
Every build makes both DXIL (Direct3D 12) and SPIR-V (Vulkan 1.3); the header for the build's backend is in `shaders/`, the other one in `shaders/other/` only to check that it compiles. DXC is a pinned release that the build downloads once ({engine}`cmake/Dxc.cmake`).
They use shader model 6.6 profiles (`vs_6_6`, `ps_6_6`), the minimum spec. Debug builds keep debug information (`-Zi -Qembed_debug -Od`), other builds are optimized and stripped (`-O3 -Qstrip_debug -Qstrip_reflect`).
The game therefore needs no shader compiler at run time and no shader files next to the exe.

## The RHI layer

The RHI is the engine's own thin layer over the graphics API. It has only what the renderer uses: a device with its swap chain, one command list per frame, static buffers, textures, pipelines, a per-frame upload ring and screen capture.
Its shape follows Direct3D 12 (recorded command lists, explicit texture barriers, bindless indices). The backend is chosen at build time; each backend implements the same classes in its own `.cpp` files, with no virtual functions.
`tools\check_platform.ps1` fails when a graphics API header (`d3d12.h`, `dxgi*.h`, `vulkan/*.h` and so on) is included outside `rhi/<api>/`.

Every pipeline uses the same bindings ({engine}`engine/shaders/Bindless.hlsli`):

| Binding | HLSL | Used for |
|---|---|---|
| 64 bytes of push constants (DX12 root constants) | `[[vk::push_constant]] ConstantBuffer<T> pc : register(b0)` | Ring index and offsets of this draw's data, atlas indices |
| Buffer array | `ByteAddressBuffer g_buffers[] : register(t0, space1)` | The upload ring (index from `Device::uploadBufferIndex`) |
| Texture array | `Texture2D g_textures[] : register(t0, space2)` | Textures (index from `Device::textureIndex`) |
| Fixed sampler | `SamplerState g_linearClamp : register(s0)` | Linear filtering, clamped |

Shaders read structures from the ring field by field with `Load`, so the C++ layout is the only layout to keep in sync.
The reasons for this shape (instead of root descriptors or `ResourceDescriptorHeap[]`) are in {engine}`docs/DECISIONS.md` (2026-10-19).

A `CommandList` binds one of two targets: `beginScene` (the back buffer's sRGB view plus depth, cleared) and `beginOverlay` (the plain view, no depth). A copy into a texture unbinds the target, so the caller binds it again after copies.

## The Vulkan backend

`MEALKIT_RHI` (CMake, set by `build.bat Vulkan` and `VulkanEditor`) chooses the backend. Direct3D 12 is the reference backend and the one shipped on Windows; the Vulkan backend has the same features, and new graphics features are built for both in the same piece of work.
The build needs no Vulkan SDK: the headers are in `third_party/vulkan-headers`, volk loads `vulkan-1.dll` (installed with the GPU driver) at run time, and the Vulkan Memory Allocator places buffers and images.

The DX12 shapes map to Vulkan like this:

| RHI | Direct3D 12 | Vulkan |
|---|---|---|
| Push constants | Root constants (16 values) | Push constant range of 64 bytes |
| Buffer and texture arrays | Two descriptor tables in one shader-visible heap | One descriptor set: storage buffer array and sampled image array (descriptor indexing, partially bound, update after bind) |
| Fixed sampler | Static sampler | Immutable sampler in the same set |
| `beginScene`, `beginOverlay` | `OMSetRenderTargets` with the sRGB or plain view | Dynamic rendering with an sRGB or UNORM view of the same swapchain image (`VK_KHR_swapchain_mutable_format`) |
| Texture barriers | Resource state transitions | Image layout transitions (synchronization2) |
| Frame pacing | Frame latency waitable object | One fence per frame in flight |
| Vsync off | `ALLOW_TEARING` | `IMMEDIATE` present mode, otherwise `MAILBOX` |

Vulkan's clip space has y pointing down. `setViewport` gives the viewport a negative height, so the same shaders and the same clockwise front faces as Direct3D 12 produce the same image.
A copy or a barrier ends the current dynamic rendering pass (Vulkan does not allow them inside one), which is why the RHI asks callers to bind the target again after copies.
With `--debug`, the Vulkan backend turns on `VK_LAYER_KHRONOS_validation` when the Vulkan SDK is installed and sends its warnings and errors to the engine log as `[Vulkan]` lines.
The minimum spec for this backend is Vulkan 1.3 with descriptor indexing, dynamic rendering, synchronization2, demote to helper invocation and `VK_KHR_swapchain_mutable_format`; Intel 11th gen integrated graphics has them.
Profile builds do not time the GPU with Tracy on Vulkan yet (the engine's own GPU timers, below, work on both backends).

## Starting up

`Renderer::init` calls `rhi::Device::init`, which in the DX12 backend:

1. Creates a DXGI 1.6 factory and picks the first hardware adapter in high-performance order that can create a Direct3D 12 device (software adapters are skipped).
2. Reads what the GPU supports (`describeGpu`): adapter name, driver version, feature level, highest shader model, resource binding tier, wave lane counts, mesh shader tier and whether memory is shared with the CPU (UMA, as on integrated graphics).
3. Refuses GPUs below the minimum (`gpuMinimumError`): shader model 6.6 and resource binding tier 3, which Intel 11th gen integrated graphics has. The message names the driver version, because an old driver on a good GPU often reports a lower shader model.
4. Creates one direct command queue and a flip-model swap chain with 3 back buffers, a frame latency waitable object (at most 2 frames queued) and tearing support when the system has it.
5. Creates two render target views per back buffer: an `R8G8B8A8_UNORM_SRGB` view for the 3D pass (the shader writes linear color and the hardware encodes gamma) and an `R8G8B8A8_UNORM` overlay view for UI and ImGui, whose colors are already sRGB.
6. Creates one shader-visible descriptor heap (16 buffer slots, then 4,096 texture slots), the upload ring with its raw buffer view in slot 0, the shared root signature and a 32-bit float depth buffer.

The renderer then creates the 3D pipeline, the UI pipeline and the two UI atlas textures.
`rhi::queryGpu` does steps 1 and 2 without a window, for `--system-info`. With the debug layer on (`--debug`), D3D12 messages are sent to the engine log.
Every D3D call goes through the `HR` macro: a failure stops the program with the error code and, after a device removal, the removal reason.

## Memory

Two frames are in flight. Each has its own command allocator and fence value, so the CPU records frame N+1 while the GPU draws frame N.

All data that changes every frame goes into **one upload buffer** of 8 MiB per frame (16 MiB in all), mapped once at start and never unmapped.
`Device::allocUpload` cuts pieces from the current frame's half with the alignment the caller asks for (16 bytes for shader data, 512 bytes for texture copies). It is a bump allocator: the offset is reset at the start of the frame, and nothing is freed one by one.
On integrated graphics the upload heap is the memory the GPU reads, so per-frame data is never copied. If a frame needs more than 8 MiB, the draw is skipped and a warning is written once.

Meshes do not change, so `createMesh` puts them in GPU buffers (`Device::createBuffer`), copied once from a temporary upload buffer at load time.
When a mesh has at most 65,535 vertices, its indices are stored as 16-bit values to save memory bandwidth.

## One frame

The engine loop ({engine}`engine/src/mealkit/game/GameMain.cpp`, and the editor in the same order) does:

1. `game->buildFrame` fills a `FrameParams` (camera, light, fog) and a `DrawList`.
2. `Frontend::afterBuildFrame` adds the screen flash from the feedback table and gives the camera to the UI and sound.
3. `Renderer::beginFrame`, `DrawList::submit`, the game UI (`ui::System::render`), the debug UI, `Renderer::endFrame`.

Inside the renderer:

- `beginFrame` calls `Device::beginFrame`, which waits on the swap chain's latency object, so the CPU never runs more than two frames ahead and input lag does not build up, then waits for this frame slot's fence and resets the allocator and the command list. The renderer then binds the scene target, clearing color to the fog color (mixed with the flash, so the sky flashes too) and depth to 0. It sets the viewport (the whole window, or the scene view in the editor), binds the 3D pipeline and writes the 176-byte frame constants into the upload ring.
- `drawInstances(mesh, instances, count)` copies the instances into the upload ring, pushes the ring index and the offsets of the frame constants and the instances, binds the mesh's vertex and index buffers and draws once.
- `drawUi` draws all UI rectangles with one more draw call (see below).
- `endFrame` calls `Device::endFrame`: the back buffer goes to the present state, the command list is closed and executed, `Present` runs (sync interval 1 with vsync, otherwise 0 and tearing allowed), the fence is signaled and the next frame slot is used.

## Instances

`render::DrawList` keeps one bucket (a `std::vector<InstanceData>`) per mesh id. `add` appends to a bucket, and `submit` draws every non-empty bucket with one draw call.
`clear` empties the buckets but keeps their memory, so a steady frame allocates nothing.

An instance is 48 bytes and is copied to the GPU as it is (`static_assert` keeps the C++ size, and the shader reads the fields at these offsets):

| Bytes | Field |
|---|---|
| 12 | position |
| 4 | color (RGBA8, sRGB) |
| 16 | rotation (quaternion) |
| 12 | scale |
| 4 | flags (`kInstanceChecker`, `kInstanceHighlight`) |

The CPU builds no matrices. The vertex shader reads the instance from the upload ring at `instanceOffset + SV_InstanceID × 48` and computes the world position as rotate(rotation, position × scale) + position.
The rotation uses the short form v + w·t + q×t with t = 2·(q×v). The normal is rotated after dividing by the scale, which keeps it correct for non-uniform scale.

A vertex is 28 bytes: position (12), normal (12) and an RGBA8 color (4) that holds the glTF material color.

## Lighting (Forward.hlsl)

Everything is drawn in one forward pass with back-face culling and reversed depth (depth cleared to 0, test `GREATER`), which spreads float depth precision more evenly over distance.

1. **Albedo** is the instance color times the vertex color. Both are sRGB bytes turned into linear color by squaring (a gamma 2.0 approximation, cheaper than the exact curve).
2. **Checker**: with flag bit 0 the albedo is darkened to 0.85 on every other 4 × 4 m cell of world x and z (the ground).
3. **Sun** uses half Lambert: h = dot(n, sun) × 0.5 + 0.5, squared. Faces turned away from the sun are dark but not black, so shapes stay readable without shadows.
4. **Ambient** is a hemisphere light: lerp(ground color, sky color, n.y × 0.5 + 0.5). Upward faces get the sky color, downward faces the ground color.
5. Color = albedo × (sun color × h² + ambient).
6. **Selection**: with flag bit 1 (editor selection) the color is mixed 45 % with orange.
7. **Fog** is exponential: f = exp(−distance × density), color = lerp(fog color, color, f).
8. **Screen flash**: the result is mixed with the flash color by its amount.

There are no textures, shadow maps or post effects yet. This keeps the pass within the budget of integrated graphics.

## UI pass (Ui.hlsl)

`ui` turns screens into a list of `UiQuad` values (112 bytes each, one rectangle) and calls `drawUi` once per frame.

- The pass draws after 3D, into the overlay view, at the full back buffer resolution, without depth and without culling.
- There is no vertex buffer. Each rectangle is one instance, and the vertex shader makes its 6 corners from `SV_VertexID`, grown by a margin for anti-aliasing and shadow blur, and rotated around the box center.
- The pixel shader computes a signed distance to a rounded box with a separate radius per corner. Coverage is saturate(0.5 − distance), which gives a one-pixel anti-aliased edge. On top of that it does solid, linear and radial fills, an inner stroke, blurred shadows (smoothstep over the blur width), images and text.
- Text samples a single-channel signed distance field atlas and turns the distance into coverage with the scale that `ui` passes per glyph, so one baked size stays sharp at every size.
- Output is premultiplied alpha, blended with `ONE, INV_SRC_ALPHA`. A clip rectangle per quad discards pixels outside it.

The two atlases are 2048 × 2048 textures: `R8_UNORM` for glyph distance fields and `R8G8B8A8_UNORM` for images. The push constants carry their texture indices.
`updateUiAtlas` can be called at any time; it queues the pixels, split into pieces of about 1 MiB. At the next `drawUi` the queued pieces are copied through the upload ring into the textures (row pitch and start alignment from `Device::copyPitch` and `copyAlignment`; in DX12, 256 and 512 bytes). Pieces that do not fit wait for the next frame.

## Screenshots

`requestCapture(path)` marks the next frame. In `Device::endFrame` the back buffer is copied into a readback buffer (layout from `GetCopyableFootprints`). After presenting, the device waits for that frame's fence and returns the RGBA pixels; the renderer writes the PNG with the platform layer's `savePng`.
The game uses it for `F12` (`screenshot.png`) and for automatic captures in tests.

## Statistics

`RenderStats` holds `drawCalls` and `instances`. `beginFrame` resets them, every `drawInstances` adds one draw call and its instance count, and `drawUi` adds one draw call.
The renderer only measures. `game::FrameStats` reads `stats()` once per frame and makes the numbers in the window title, the F1 overlay and the perf log, as decided in {engine}`docs/CODING_MODEL.md` ("성능 숫자 모으기와 보여 주기").
Profile builds also time the GPU frame with Tracy's D3D12 zones.

### GPU time and memory

The RHI times the GPU with timestamp queries in every build: `CommandList::beginTimer(n)`/`endTimer(n)` for up to `rhi::kMaxGpuTimers` (8) sections, plus the whole command list.
Each frame in flight has its own slots (a D3D12 query heap resolved into a mapped readback buffer; a Vulkan query pool reset at the start of the frame). `beginFrame` reads them after waiting for that frame's fence, so `Device::gpuTimes()` is two frames old and never makes the CPU wait.
Only written queries are resolved or read. The meaning of the numbers is the renderer's: `render::GpuPass` (opaque, shadow, post, vfx, ui) with the 3D pass from `beginFrame` to `beginOverlay` and the UI pass (game UI and debug UI) after it. `RenderStats` carries the last values (`gpuValid`, `gpuFrameMs`, `gpuPassMs`).

`Device::gpuMemory()` returns the memory used and the budget: `IDXGIAdapter3::QueryVideoMemoryInfo` (local segment) on Direct3D 12, VMA's heap budgets over the device-local heaps on Vulkan (`VK_EXT_memory_budget` when the driver has it, otherwise VMA's own estimate). On integrated graphics the local segment is shared system memory.

`Renderer::device()` gives the RHI device to the ImGui layer (see {doc}`debug`), so the debug UI draws into the same frame.

## Techniques used

### Frame structure

| Technique | Where | What it does |
|---|---|---|
| Frames in flight with fences | `Device::Impl::frames`, `waitForFence` | Two command allocators and fence values let the CPU record one frame while the GPU draws the previous one. |
| Frame latency waitable swap chain | `Device::beginFrame` | Waits until the swap chain can take a frame, with at most 2 queued, to keep input lag low. |
| Flip model with tearing | `Device::init`, `Device::endFrame` | `FLIP_DISCARD` with 3 buffers. With vsync off and tearing supported, frames are presented at once. |
| Persistently mapped upload ring | `Device::allocUpload` | One mapped buffer split into a half per frame. Allocation is an aligned bump of an offset, reset every frame. On UMA GPUs it needs no copy. |
| Two views of one back buffer | `createSwapchainResources` | An sRGB view lets the hardware do gamma encoding for 3D. A plain view lets UI and ImGui write sRGB colors unchanged. |
| Reversed depth | `Device::createPipeline` | Depth is cleared to 0 and tested with `GREATER`, which gives float depth more even precision over distance. |
| Build-time shader compilation | `mealkit_shader` in `engine/CMakeLists.txt` | DXC turns HLSL into byte arrays in headers, so the exe carries its shaders and needs no compiler. |

### Drawing

| Technique | Where | What it does |
|---|---|---|
| One binding layout for all pipelines | `createRootSignature`, `Bindless.hlsli` | Push constants, a buffer array, a texture array and one sampler. Draws change only push constants and vertex and index buffers. |
| Bindless arrays | `g_buffers[]`, `g_textures[]` | Shaders pick a buffer or texture by index, so no descriptor is written per draw. |
| Instanced drawing per mesh | `DrawList`, `drawInstances` | All instances of a mesh are one draw call. Buckets keep their memory between frames. |
| Shader-side transforms | `VSMain` in `Forward.hlsl` | The CPU writes position, quaternion and scale; the vertex shader rotates with the quaternion formula, so no matrices are built per object. |
| 16-bit indices | `createMesh` | Meshes with at most 65,535 vertices use half the index memory. |
| Half Lambert lighting | `PSMain` in `Forward.hlsl` | Wraps the diffuse term to 0..1 and squares it, so shadowed sides keep some shape. |
| Hemisphere ambient light | `PSMain` | Blends a ground and a sky color by the normal's height, a cheap stand-in for light from the surroundings. |
| Exponential fog | `PSMain` | exp(−distance × density) hides the far end of the scene and gives depth. |
| Gamma 2.0 approximation | `unpackAlbedo` | Squares sRGB values instead of the exact curve; the hardware does the exact encoding on output. |

### UI and output

| Technique | Where | What it does |
|---|---|---|
| Vertex-buffer-free quads | `VSMain` in `Ui.hlsl` | Each rectangle is an instance and its corners come from `SV_VertexID`. |
| Signed distance shapes | `roundBox` in `Ui.hlsl` | Rounded boxes with a radius per corner, anti-aliased by turning distance into coverage. |
| SDF text | `PSMain` in `Ui.hlsl` | Glyph outlines stored as distance fields stay sharp when scaled. |
| Premultiplied alpha | UI pipeline | Blending with `ONE, INV_SRC_ALPHA` composes nested transparency correctly. |
| Queued atlas uploads | `updateUiAtlas`, `flushUiUploads` | Atlas changes are queued on the CPU and copied in the next frame through the same upload ring. |
| Readback capture | `Device::endFrame`, `savePng` | Copies the back buffer to a readback heap after the fence and writes it as PNG through the platform layer. |
