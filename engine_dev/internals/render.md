# Render

This page explains how the DirectX 12 renderer works inside: how it starts, what one frame does, how instances reach the GPU, how the shaders light the scene, and how the 2D UI pass, screenshots and statistics work.
The frame budget and the profiler are in {doc}`../../manual/performance`. The code is in {engine}`engine/src/mealkit/render` and the shaders in {engine}`engine/shaders`.

`render` comes after `scene` in the folder order of {engine}`docs/CODING_MODEL.md` ("엔진 폴더 사이 의존"). The `rhi` folder (a thin layer over the graphics API) will sit between them in stage 2; today the renderer calls Direct3D 12 directly.
`asset`, `debug` and `ui` come after it and give it meshes, ImGui draw data and UI rectangles.

## Files

| File | Holds |
|---|---|
| {engine}`engine/src/mealkit/render/Renderer.h` | `Renderer`, the per-frame values (`FrameParams`), the 48-byte `InstanceData`, the 112-byte `UiQuad`, GPU information and `RenderStats`. |
| {engine}`engine/src/mealkit/render/Renderer.cpp` | The whole DX12 implementation. No D3D type appears in a header, so the rest of the engine never includes `d3d12.h`. |
| {engine}`engine/src/mealkit/render/DrawList.h` | Collects instances per mesh for one frame. |
| {engine}`engine/src/mealkit/render/Mesh.h` | The 28-byte `Vertex`, `MeshData` and the unit box. |
| {engine}`engine/shaders/Forward.hlsl` | The 3D shader: instance transform, lighting and fog. |
| {engine}`engine/shaders/Ui.hlsl` | The 2D UI shader: rounded boxes, gradients, shadows, images and SDF text. |

The shaders are compiled at build time by DXC into header files with byte arrays (`g_ForwardVS.h`, `g_UiPS.h`, ...), see {engine}`engine/CMakeLists.txt`.
They use shader model 6.0 profiles (`vs_6_0`, `ps_6_0`). Debug builds keep debug information (`-Zi -Qembed_debug -Od`), other builds are optimized and stripped (`-O3 -Qstrip_debug -Qstrip_reflect`).
The game therefore needs no shader compiler at run time and no shader files next to the exe.

## Starting up

`Renderer::init`:

1. Creates a DXGI 1.6 factory and picks the first hardware adapter in high-performance order that can create a Direct3D 12 device (software adapters are skipped).
2. Reads what the GPU supports (`describeGpu`): adapter name, driver version, feature level, highest shader model, resource binding tier, wave lane counts, mesh shader tier and whether memory is shared with the CPU (UMA, as on integrated graphics).
3. Refuses GPUs below the minimum (`gpuMinimumError`): shader model 6.6 and resource binding tier 3, which Intel 11th gen integrated graphics has. The message names the driver version, because an old driver on a good GPU often reports a lower shader model.
4. Creates one direct command queue and a flip-model swap chain with 3 back buffers, a frame latency waitable object (at most 2 frames queued) and tearing support when the system has it.
5. Creates two render target views per back buffer: an `R8G8B8A8_UNORM_SRGB` view for the 3D pass (the shader writes linear color and the hardware encodes gamma) and an `R8G8B8A8_UNORM` overlay view for UI and ImGui, whose colors are already sRGB.
6. Creates a 32-bit float depth buffer, the upload ring, the 3D pipeline and the UI pipeline.

`queryGpu` does steps 1 and 2 without a window, for `--system-info`. With the debug layer on, D3D12 messages are sent to the engine log.
Every D3D call goes through the `HR` macro: a failure stops the program with the error code and, after a device removal, the removal reason.

## Memory

Two frames are in flight. Each has its own command allocator and fence value, so the CPU records frame N+1 while the GPU draws frame N.

All data that changes every frame goes into **one upload buffer** of 8 MiB per frame (16 MiB in all), mapped once at start and never unmapped.
`allocUpload` cuts pieces from the current frame's half with 256-byte alignment, which is what constant buffer views need. It is a bump allocator: the offset is reset at the start of the frame, and nothing is freed one by one.
On integrated graphics the upload heap is the memory the GPU reads, so per-frame data is never copied. If a frame needs more than 8 MiB, the draw is skipped and a warning is written once.

Meshes do not change, so `createMesh` puts them in default-heap buffers, copied once from a temporary upload buffer at load time.
When a mesh has at most 65,535 vertices, its indices are stored as 16-bit values to save memory bandwidth.

## One frame

The engine loop ({engine}`engine/src/mealkit/game/GameMain.cpp`, and the editor in the same order) does:

1. `game->buildFrame` fills a `FrameParams` (camera, light, fog) and a `DrawList`.
2. `Frontend::afterBuildFrame` adds the screen flash from the feedback table and gives the camera to the UI and sound.
3. `Renderer::beginFrame`, `DrawList::submit`, the game UI (`ui::System::render`), the debug UI, `Renderer::endFrame`.

Inside the renderer:

- `beginFrame` waits on the swap chain's latency object, so the CPU never runs more than two frames ahead and input lag does not build up. It waits for this frame slot's fence, resets the allocator and the command list, moves the back buffer to the render target state, clears color to the fog color (mixed with the flash, so the sky flashes too) and depth to 0. It sets the viewport (the whole window, or the scene view in the editor) and writes the 176-byte frame constants into the upload ring.
- `drawInstances(mesh, instances, count)` copies the instances into the upload ring, binds that address as a root shader resource view, binds the mesh's vertex and index buffers and calls `DrawIndexedInstanced` once.
- `drawUi` draws all UI rectangles with one more draw call (see below).
- `endFrame` moves the back buffer to the present state, closes and executes the command list, calls `Present` (sync interval 1 with vsync, otherwise 0 and tearing allowed), signals the fence and moves to the next frame slot.

## Instances

`render::DrawList` keeps one bucket (a `std::vector<InstanceData>`) per mesh id. `add` appends to a bucket, and `submit` draws every non-empty bucket with one draw call.
`clear` empties the buckets but keeps their memory, so a steady frame allocates nothing.

An instance is 48 bytes and is copied to the GPU as it is (`static_assert` keeps the C++ and HLSL layouts equal):

| Bytes | Field |
|---|---|
| 12 | position |
| 4 | color (RGBA8, sRGB) |
| 16 | rotation (quaternion) |
| 12 | scale |
| 4 | flags (`kInstanceChecker`, `kInstanceHighlight`) |

The CPU builds no matrices. The vertex shader reads the instance from a `StructuredBuffer` with `SV_InstanceID` and computes the world position as rotate(rotation, position × scale) + position.
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

The two atlases are 2048 × 2048 textures: `R8_UNORM` for glyph distance fields and `R8G8B8A8_UNORM` for images, both in one shader-visible descriptor heap with a linear clamp sampler.
`updateUiAtlas` can be called at any time; it queues the pixels, split into pieces of about 1 MiB. At the next `drawUi` the queued pieces are copied through the upload ring into the textures (rows aligned to 256 bytes, data to 512 bytes, as D3D12 requires). Pieces that do not fit wait for the next frame.

## Screenshots

`requestCapture(path)` marks the next frame. In `endFrame` the back buffer is copied into a readback buffer (layout from `GetCopyableFootprints`). After presenting, the renderer waits for that frame's fence, converts RGBA to BGRA and writes a PNG with the Windows Imaging Component.
The game uses it for `F12` (`screenshot.png`) and for automatic captures in tests.

## Statistics

`RenderStats` holds `drawCalls` and `instances`. `beginFrame` resets them, every `drawInstances` adds one draw call and its instance count, and `drawUi` adds one draw call.
The renderer only measures. `game::FrameStats` reads `stats()` once per frame and makes the numbers in the window title, the F1 overlay and the perf log, as decided in {engine}`docs/CODING_MODEL.md` ("성능 숫자 모으기와 보여 주기").
Profile builds also time the GPU frame with Tracy's D3D12 zones.

`native()` gives the device, queue, command list, frame count and overlay format to the ImGui layer (see {doc}`debug`), so it can draw into the same frame.

## Techniques used

### Frame structure

| Technique | Where | What it does |
|---|---|---|
| Frames in flight with fences | `Renderer::Impl::frames`, `waitForFence` | Two command allocators and fence values let the CPU record one frame while the GPU draws the previous one. |
| Frame latency waitable swap chain | `beginFrame` | Waits until the swap chain can take a frame, with at most 2 queued, to keep input lag low. |
| Flip model with tearing | `init`, `endFrame` | `FLIP_DISCARD` with 3 buffers. With vsync off and tearing supported, frames are presented at once. |
| Persistently mapped upload ring | `allocUpload` | One mapped buffer split into a half per frame. Allocation is a 256-byte aligned bump of an offset, reset every frame. On UMA GPUs it needs no copy. |
| Two views of one back buffer | `createSwapchainResources` | An sRGB view lets the hardware do gamma encoding for 3D. A plain view lets UI and ImGui write sRGB colors unchanged. |
| Reversed depth | `createPipeline` | Depth is cleared to 0 and tested with `GREATER`, which gives float depth more even precision over distance. |
| Build-time shader compilation | `mealkit_shader` in `engine/CMakeLists.txt` | DXC turns HLSL into byte arrays in headers, so the exe carries its shaders and needs no compiler. |

### Drawing

| Technique | Where | What it does |
|---|---|---|
| Instanced drawing per mesh | `DrawList`, `drawInstances` | All instances of a mesh are one draw call. Buckets keep their memory between frames. |
| Shader-side transforms | `VSMain` in `Forward.hlsl` | The CPU writes position, quaternion and scale; the vertex shader rotates with the quaternion formula, so no matrices are built per object. |
| Root shader resource view per draw | `drawInstances` | The instance buffer is bound by GPU address, with no descriptor to create. |
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
| Readback capture | `endFrame`, `savePng` | Copies the back buffer to a readback heap and encodes it as PNG with WIC after the fence. |
