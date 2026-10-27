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
| {engine}`engine/src/mealkit/render/Mesh.h` | The 36-byte `Vertex`, `MeshData` and the unit box. |
| {engine}`engine/src/mealkit/asset/TextureCache.h` | Model textures: decoding, mipmaps, BC7/BC5 compression and the cache files. |
| {engine}`engine/shaders/Bindless.hlsli` | The binding layout that every shader shares. |
| {engine}`engine/shaders/Forward.hlsl` | The 3D shader: instance transform, lighting and fog. |
| {engine}`engine/shaders/Ui.hlsl` | The 2D UI shader: rounded boxes, gradients, shadows, images and SDF text. |

The shaders are compiled at build time by DXC into header files with byte arrays (`g_ForwardVS.h`, `g_UiPS.h`, ...), see {engine}`engine/CMakeLists.txt`.
Every build makes both DXIL (Direct3D 12) and SPIR-V (Vulkan 1.3); the header for the build's backend is in `shaders/`, the other one in `shaders/other/` only to check that it compiles. DXC is a pinned release that the build downloads once ({engine}`cmake/Dxc.cmake`).
They use shader model 6.6 profiles (`vs_6_6`, `ps_6_6`), the minimum spec. Debug builds keep debug information (`-Zi -Qembed_debug -Od`), other builds are optimized and stripped (`-O3 -Qstrip_debug -Qstrip_reflect`).
The game therefore needs no shader compiler at run time and no shader files next to the exe.

In development builds (every build with the debug UI, not `build.bat Export`) the shaders can be edited while the game or the editor runs. `render::ShaderReloader` ({engine}`engine/src/mealkit/render/ShaderReload.h`) checks the files in `engine/shaders` every half second, compiles a changed shader (all of them when `Bindless.hlsli` changes) with the same DXC and options as the build in a background process, and swaps the pipeline with `rhi::Device::recreatePipeline` before the next frame. The log says `Shader reloaded: Forward.hlsl`. A compile error is logged with DXC's output and the old shader stays in use. On a PC without the engine folder or DXC, reloading is off.

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

A `CommandList` binds the back buffer with `beginOverlay` (its plain `UNORM` view, no depth: post processing and UI write sRGB values) or an offscreen target with `beginTarget`. A copy into a texture unbinds the target, so the caller binds it again after copies.

## The Vulkan backend

`MEALKIT_RHI` (CMake, set by `build.bat Vulkan` and `VulkanEditor`) chooses the backend. Direct3D 12 is the reference backend and the one shipped on Windows; the Vulkan backend has the same features, and new graphics features are built for both in the same piece of work.
The build needs no Vulkan SDK: the headers are in `third_party/vulkan-headers`, volk loads `vulkan-1.dll` (installed with the GPU driver) at run time, and the Vulkan Memory Allocator places buffers and images.

The DX12 shapes map to Vulkan like this:

| RHI | Direct3D 12 | Vulkan |
|---|---|---|
| Push constants | Root constants (16 values) | Push constant range of 64 bytes |
| Buffer and texture arrays | Two descriptor tables in one shader-visible heap | One descriptor set: storage buffer array and sampled image array (descriptor indexing, partially bound, update after bind) |
| Fixed sampler | Static sampler | Immutable sampler in the same set |
| `beginOverlay`, `beginTarget` | `OMSetRenderTargets` with the back buffer's view or the target's views | Dynamic rendering with the swapchain image's `UNORM` view or the target's image |
| Texture barriers | Resource state transitions | Image layout transitions (synchronization2) |
| Frame pacing | Frame latency waitable object | One fence per frame in flight |
| Vsync off | `ALLOW_TEARING` | `IMMEDIATE` present mode, otherwise `MAILBOX` |

Vulkan's clip space has y pointing down. `setViewport` gives the viewport a negative height, so the same shaders and the same clockwise front faces as Direct3D 12 produce the same image.
A copy or a barrier ends the current dynamic rendering pass (Vulkan does not allow them inside one), which is why the RHI asks callers to bind the target again after copies.
With `--debug`, the Vulkan backend turns on `VK_LAYER_KHRONOS_validation` when the Vulkan SDK is installed and sends its warnings and errors to the engine log as `[Vulkan]` lines.
The minimum spec for this backend is Vulkan 1.3 with descriptor indexing, dynamic rendering, synchronization2, demote to helper invocation and a `B10G11R11` format that can be drawn, blended and filtered (the HDR scene target); Intel 11th gen integrated graphics has them.
Profile builds do not time the GPU with Tracy on Vulkan yet (the engine's own GPU timers, below, work on both backends).

## Starting up

`Renderer::init` calls `rhi::Device::init`, which in the DX12 backend:

1. Creates a DXGI 1.6 factory and picks the first hardware adapter in high-performance order that can create a Direct3D 12 device (software adapters are skipped).
2. Reads what the GPU supports (`describeGpu`): adapter name, driver version, feature level, highest shader model, resource binding tier, wave lane counts, mesh shader tier and whether memory is shared with the CPU (UMA, as on integrated graphics).
3. Refuses GPUs below the minimum (`gpuMinimumError`): shader model 6.6 and resource binding tier 3, which Intel 11th gen integrated graphics has. The message names the driver version, because an old driver on a good GPU often reports a lower shader model.
4. Creates one direct command queue and a flip-model swap chain with 3 back buffers, a frame latency waitable object (at most 2 frames queued) and tearing support when the system has it.
5. Creates two render target views per back buffer: an `R8G8B8A8_UNORM_SRGB` view for the 3D pass (the shader writes linear color and the hardware encodes gamma) and an `R8G8B8A8_UNORM` overlay view for UI and ImGui, whose colors are already sRGB.
6. Creates one shader-visible descriptor heap (16 buffer slots, then 4,096 texture slots), the upload ring with its raw buffer view in slot 0, the shared root signature and a 32-bit float depth buffer.

The renderer then creates every 3D pipeline it can use (one per lighting model, the outline pass and, in builds with the debug UI, the two view-mode pipelines), the UI pipeline, the two UI atlas textures and the toon ramp texture. Because all of them exist before the first frame, switching the lighting model or meeting a new material feature never compiles anything during play.
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

- `beginFrame` calls `Device::beginFrame`, which waits on the swap chain's latency object, so the CPU never runs more than two frames ahead and input lag does not build up, then waits for this frame slot's fence and resets the allocator and the command list. The scene target is bound at the first draw (so the shadow pass can draw first), clearing color to the fog color (mixed with the flash, so the sky flashes too) and depth to 0. It sets the viewport (the whole window, or the scene view in the editor), binds the pipeline of the current lighting model and writes the 672-byte frame constants (camera, light, fog, flash, the material table position, wind, the toon ramp texture number, the inverse view-projection, cube numbers, intensity, rotation and SH coefficients of the sky HDRI, the reflection probe table, the point light table and the shadow cascades) into the upload ring. Queued texture copies (UI atlas pieces, a new toon ramp) are done first.
- `drawInstances(mesh, instances, count)` copies the instances into the upload ring, pushes the ring index and the offsets of the frame constants and the instances, binds the mesh's vertex and index buffers and draws once. If the mesh has an outlined material, it draws the same instances a second time with the outline pipeline (see below).
- `drawUi` draws all UI rectangles with one more draw call (see below).
- `endFrame` calls `Device::endFrame`: the back buffer goes to the present state, the command list is closed and executed, `Present` runs (sync interval 1 with vsync, otherwise 0 and tearing allowed), the fence is signaled and the next frame slot is used.

## Instances

`render::DrawList` keeps one bucket (a `std::vector<InstanceData>`) per mesh id. `add` appends to a bucket, and `submit` draws every non-empty bucket with one draw call.
`clear` empties the buckets but keeps their memory, so a steady frame allocates nothing.

`submit` runs after `beginFrame` and leaves out instances outside the view (frustum culling, {engine}`engine/src/mealkit/render/Culling.h`). `createMesh` keeps a bounding sphere per mesh (the center of the vertex box and the farthest vertex). For each instance the sphere is moved, rotated and scaled by the largest scale axis, then tested against the six planes `beginFrame` takes from `viewProj`. Only the visible instances are copied to the upload ring. Culled instances count in `RenderStats::culled`. Grouping instances into chunks to cull many at once is left for scenes with tens of thousands of objects.

An instance is 48 bytes and is copied to the GPU as it is (`static_assert` keeps the C++ size, and the shader reads the fields at these offsets):

| Bytes | Field |
|---|---|
| 12 | position |
| 4 | color (RGBA8, sRGB) |
| 16 | rotation (quaternion) |
| 12 | scale |
| 4 | flags: bit 0 `kInstanceChecker`, bit 1 `kInstanceHighlight`, bit 2 `kInstanceOverBudget`, bits 8 to 9 LOD (view modes), bits 16 to 23 flash, bits 24 to 31 dissolve progress |

The two style values in the top 16 bits are 0 to 255 for 0 to 1, written with `render::instanceFlash(flags, amount)` and `render::instanceDissolve(flags, progress)`. Keeping them in the flags keeps the instance at 48 bytes.

The CPU builds no matrices. The vertex shader reads the instance from the upload ring at `instanceOffset + SV_InstanceID × 48` and computes the world position as rotate(rotation, position × scale) + position.
The rotation uses the short form v + w·t + q×t with t = 2·(q×v). The normal is rotated after dividing by the scale, which keeps it correct for non-uniform scale.

A vertex is 36 bytes: position (12), normal (12), an RGBA8 color (4, glTF `COLOR_0`), the texture coordinate as two halves (4) and the material number (2, plus 2 reserved).
There is no tangent: the pixel shader builds the tangent frame for normal maps from screen-space derivatives of the position and the texture coordinate.

### Materials and textures

`Renderer::createMaterial` adds a 128-byte record (base color, emissive, alpha cutoff, metallic, roughness, normal scale, four bindless texture numbers, then the style feature bits and their values: outline width and color, rim strength and color, dissolve edge width and glow color, wind strength) to a table; material 0 is plain white. Every frame the whole table is written to the upload ring after the frame constants, and the shader reads `materials[vertex.material]`. A model with several materials is still one mesh and one draw call per LOD.
`ModelCache` turns each glTF material into such a record while loading. Each image goes through `asset::loadCompressedTexture`: the cache file name is a hash of the encoded image, the usage and the cache version. On a miss (development builds only) the image is decoded with stb_image, mipmaps are made with a 2 × 2 box filter (in linear space for color, renormalized for normals) and every 4 × 4 block is compressed with bc7enc (BC7, sRGB for color) or rgbcx (BC5 for normals). `Device::createTexture(TextureInit)` uploads all mips at once. Textures are sampled with the second fixed sampler `g_linearWrap` (repeat, 8× anisotropic).

## Style presets

Artists choose a look instead of writing shaders ({engine}`docs/CODING_MODEL.md` "셰이더 코드"):

- The **lighting model** is one project setting for the whole game (`lightingModel`: `Pbr`, `Toon` or `Unlit`). `Forward.hlsl` is compiled three times with `LIGHTING_MODEL=0/1/2` (`g_ForwardPbrPS`, `g_ForwardToonPS`, `g_ForwardUnlitPS`), all three are in the executable, and `Renderer::setLightingModel` only picks which pipeline `beginFrame` binds. `game::applyRenderStyle` passes the setting (and the toon ramp image) from `mealkit.project`; the editor calls it again when the setting or the ramp file changes.
- **Material features** are bits in the material record, not shader variants: `kMaterialOutline`, `kMaterialWind`, `kMaterialRim` and `kMaterialDissolve`. The shader tests the bits. Materials with different features can share a mesh, so a model is still one draw call (plus one for the outline).
- **Per-instance values** (flash, dissolve progress) are in the instance flags (above). Game view code sets them from tick events.

The features:

| Feature | Where | How |
|---|---|---|
| Outline | second pass, `VSOutline`/`PSOutline` | The mesh is drawn again with front faces culled (`PipelineDesc::cullFront`) and every vertex pushed out along its normal by the outline width (metres, world space). Only the grown back faces are left around the object, in the outline color. Vertices of materials without the feature are collapsed to a zero-area triangle, which the rasterizer drops. Hard edges (split normals) leave gaps; smooth the normals of outlined meshes. |
| Wind | vertex shader | The world position moves along the wind direction by sin(time × 1.7 + phase) × 0.7 + sin(time × 3.3 + 1.9 phase) × 0.3, times the vertex color alpha, the material's wind strength and `FrameParams::windStrength`. The phase comes from the world position, so neighbours do not sway together. `FrameParams::time` is the screen time (0 in golden images). |
| Rim | pixel shader | Adds rim color × strength × (1 − n·v)³ after lighting. |
| Dissolve | pixel shader (both passes) | Two octaves of integer-hash value noise on the object-space position. Pixels whose noise is below progress × (1 + edge) are discarded, and the band above that glows with the dissolve color. Progress 1 removes everything. |
| Flash | pixel shader (both passes) | The color is mixed with white by the flash amount before fog, for every material. |

## Lighting (Forward.hlsl)

Everything is drawn in one forward pass with back-face culling and reversed depth (depth cleared to 0, test `GREATER`), which spreads float depth precision more evenly over distance.

1. **Albedo** is the instance color times the vertex color (sRGB bytes turned into linear color by squaring, a gamma 2.0 approximation) times the material base color and its texture. With alpha clip, pixels under the cutoff are discarded. The normal map, metallic-roughness texture (G = roughness, B = metallic) and emissive texture are read the same way.
2. **Checker**: with flag bit 0 the albedo is darkened to 0.85 on every other 4 × 4 m cell of world x and z (the ground).
3. **Sun** uses half Lambert: h = dot(n, sun) × 0.5 + 0.5, squared. Faces turned away from the sun are dark but not black, so shapes stay readable without shadows.
4. **Ambient**: with a sky HDRI, the 9 spherical harmonics coefficients evaluated at the normal (rotated by the HDRI rotation, times its intensity). Without one, a hemisphere light: lerp(ground color, sky color, n.y × 0.5 + 0.5).
5. **Specular**: GGX with a Smith visibility term and Schlick Fresnel for the sun, F0 = 0.04 for non-metals and the albedo for metals. With a sky HDRI the environment reflection is the reflection cube sampled along reflect(−v, n) at mip roughness × (mips − 1), times Karis' analytic approximation of the split-sum BRDF (no lookup texture). Without one, a rough guess (F0 × ambient) stands in.
6. Color = albedo × (1 − metallic) × (sun color × h² + ambient) + specular + emissive. This is the `Pbr` lighting model. `Toon` replaces h² by the toon ramp texture sampled at h (a 256 × 1 texture: the project's ramp image, nearest pixel, or 3 grey steps by default) and the GGX highlight by one hard-edged highlight. `Unlit` uses albedo + emissive only.
7. **Rim and dissolve glow** are added (see the table above).
8. **Selection**: with flag bit 1 (editor selection) the color is mixed 45 % with orange.
9. **Flash**: the instance flash mixes the color with white. **Fog** is exponential: f = exp(−distance × density), color = lerp(fog color, color, f).
10. **Screen flash**: the result is mixed with the flash color by its amount.

There are no shadow maps or post effects yet. This keeps the pass within the budget of integrated graphics.

## UI pass (Ui.hlsl)

`ui` turns screens into a list of `UiQuad` values (112 bytes each, one rectangle) and calls `drawUi` once per frame.

- The pass draws after 3D, into the overlay view, at the full back buffer resolution, without depth and without culling.
- There is no vertex buffer. Each rectangle is one instance, and the vertex shader makes its 6 corners from `SV_VertexID`, grown by a margin for anti-aliasing and shadow blur, and rotated around the box center.
- The pixel shader computes a signed distance to a rounded box with a separate radius per corner. Coverage is saturate(0.5 − distance), which gives a one-pixel anti-aliased edge. On top of that it does solid, linear and radial fills, an inner stroke, blurred shadows (smoothstep over the blur width), images and text.
- Text samples a single-channel signed distance field atlas and turns the distance into coverage with the scale that `ui` passes per glyph, so one baked size stays sharp at every size.
- Output is premultiplied alpha, blended with `ONE, INV_SRC_ALPHA`. A clip rectangle per quad discards pixels outside it.

The two atlases are 2048 × 2048 textures: `R8_UNORM` for glyph distance fields and `R8G8B8A8_UNORM` for images. The push constants carry their texture indices.
`updateUiAtlas` can be called at any time; it queues the pixels, split into pieces of about 1 MiB. At the next `beginFrame` or `drawUi` the queued pieces are copied through the upload ring into the textures (row pitch and start alignment from `Device::copyPitch` and `copyAlignment`; in DX12, 256 and 512 bytes). Pieces that do not fit wait for the next frame.

## Sky HDRI

`asset::loadEnvironment` ({engine}`engine/src/mealkit/asset/Environment.cpp`) turns an equirectangular `.hdr` into three things, baked on the CPU and cached in `build/cache/environments/<content hash>.mkenv`:

- a **sky cube** (face size = image width / 4, at most 512) for the skybox,
- a **reflection cube**, 128² with 6 mips: mip 0 is the sky itself, mip k is prefiltered for roughness k / 5 with 64 GGX importance samples per texel, each read from a lower mip of the image chosen from the sample's solid angle (filtered importance sampling) to keep noise down,
- 9 **spherical harmonics** coefficients of the radiance, already multiplied by the Lambert convolution factors, so evaluating them at a normal gives the ambient color directly.

Texels brighter than 16 are clamped for the reflection and ambient bake: the sun in the image would otherwise add a second sun on top of the scene's sun light. Cube texels are `Rgb9e5` (4 bytes, shared exponent). Faces follow the DX12/Vulkan order and orientation (+X, −X, +Y, −Y, +Z, −Z), which matches MealKit's left-handed y-up world.

The RHI has cube textures for this: `TextureInit::cube` uploads six faces with their mips, and shaders read `TextureCube g_cubes[]`, which uses the same index space as `g_textures[]` (in DX12 a second descriptor table over the same heap range in `space3`, in Vulkan binding 4 written at the same slot).
`Renderer::createEnvironment` uploads the two cubes and keeps the coefficients; `FrameParams::environment` picks one per frame (0 = none). When one is set, `beginFrame` (and `drawToTarget`) first draws the sky: a full-screen triangle without depth, whose pixel shader turns the screen position into a world direction with the inverse view-projection matrix. 3D drawing then covers it. Fog does not apply to the sky.
`ModelCache::environment(path)` loads each HDRI once and returns its number, or 0 with one warning when the file is missing or cannot be read; editor hot reload bakes a changed file again on its next use.

## Reflection probes

A `reflection_probe` scene object (a built-in type, view-only like the sky, its scale is the box it affects) gives that box its own reflection cube. The editor bakes it (`Editor::renderProbeBake`): each frame one cube face is drawn into an offscreen target with a 90° camera at the probe's position (objects visible in the game only, sky reflection, no probes), and `Renderer::captureTarget` reads the target back at `endFrame` (`rhi::Capture::source`, DX12 and Vulkan). After six faces `asset::bakeProbe` makes the same kind of reflection cube as the sky HDRI (mip 0 a mirror, then GGX samples, RGB9E5) and `asset::saveProbe` writes `assets/probes/<scene>_<id>.mkprobe`; the object's `bake` field keeps the path.

At run time `ModelCache::probes(scene, out)` uploads the files (`Renderer::createProbe`) and returns the position, half size and number of each baked probe, up to the project setting `probeMaxCount`. The frame writes them into the upload ring as a table of 32 bytes per probe. The vertex shader picks, for each instance, the probe whose box contains the instance position and whose center is nearest, and the pixel shader reads that cube instead of the sky's reflection cube (without the HDRI rotation and intensity, which the capture already contains). Probe faces are drawn without tone mapping and captured as 8-bit sRGB, so light brighter than 1 is clipped.

## Point lights

A `point_light` scene object (a built-in type whose fields come from `scene::PointLightFields`: color, intensity, range) becomes a `render::PointLight` through `render::addSceneLights` (world position, linear color × intensity); view code may add more lights to `FrameParams::lights` (up to 255 per frame). The frame writes them as a table of 32 bytes per light. `drawInstances` then picks, for each instance, the lights that reach the mesh's bounding sphere, keeping the strongest by brightness × closeness, up to `setLightsPerObject` (project setting `pointLightsPerObject`, 4 by default, 8 at most). It writes eight 8-bit light numbers per instance (0xFF ends the list) into the upload ring and passes the offset in the push constants; frames without lights skip all of this.

The vertex shader passes the eight numbers on, and the pixel shader adds each light with a windowed inverse-square falloff (zero at the range): Lambert diffuse plus the same GGX specular as the sun for `Pbr`, the toon ramp for `Toon`, nothing for `Unlit`. Point lights have no shadows.

## Sun shadows

The sun casts shadows through cascaded shadow maps (project settings `shadows`, `shadowCascades` 1–2, `shadowMapSize` 1024, `shadowDistance` 40 m; `Renderer::setShadows`). `beginFrame` splits the camera's view up to the shadow distance into one or two slices (the first ends at a quarter of the distance), wraps each slice in a sphere and builds an orthographic light projection around it. The sphere radius and the center (in light space) are rounded to whole shadow-map texels, so the shadow edges do not crawl when the camera turns or moves; the box reaches 100 m further toward the sun, so objects outside the view still cast shadows into it.

The cascades sit side by side in one depth-only target (`rhi::Device::createDepthTarget`, D32 written, read as R32 float). `DrawList::submit` calls `Renderer::drawShadows` first: every instance of the list (before camera culling), culled per cascade against the light box, is drawn with the `VSShadow`/`PSShadow` pipeline (`rhi::Target::Shadow`, no color, both faces, alpha mask and dissolve still cut holes). Only then is the scene target bound. The pixel shader picks the cascade by the distance along the camera's forward direction, pushes the point along the normal by 1.5 texels against self-shadowing, and filters with four `GatherRed` reads (a 4 × 4 texel area with bilinear weights). Shadows fade out over the last 10 % of the distance and on faces that already turn away from the sun. They darken only the sun's diffuse and specular light; the toon model moves shadowed pixels to the dark half of its ramp. Offscreen views (look dev, probe baking) draw without shadows.

## Skinned meshes

`asset::ModelCache` reads the first glTF skin (`asset/Animation.h`): joints are reordered so a parent comes before its children, inverse bind matrices and rest poses are kept in glTF space, and every animation is baked into a clip of joint poses at 30 Hz (linear keys, rotations by nlerp; step keys hold; cubic-spline keys use their values only). A skinned mesh has no LODs and its vertices carry four joint numbers (8-bit) and weights (8-bit, summing to 255) after the 36-byte vertex, 44 bytes in all; static parts of a skinned model follow their nearest ancestor joint.

`asset::skinPalette` turns a pose into joint world matrices × inverse bind matrices, mirrored into MealKit's left-handed space, as three rows per joint (48 bytes). `DrawList::addSkinned` keeps one instance and its palette; the renderer uploads the palette into the ring, passes its offset in the push constants and draws each skinned instance with its own draw call through the skinned pipelines (the same shaders compiled with `SKINNED=1`, which add the `JOINTS`/`WEIGHTS` attributes and blend four palette matrices in the vertex shader). Shadows, outlines and point lights work the same way; culling uses the bind-pose bounds enlarged by half.

## Post processing

The main 3D is drawn into an HDR scene target the size of the window (`Renderer::Impl::mainChain`, made again outside the frame when the window size changes). The first of `drawToTarget`, `beginOverlay`, `drawUi` and `endFrame` resolves it (`resolveScene`, GPU pass `post`): bloom goes down a chain of five half-size `Hdr` targets (`PSBloomDown`: four diagonal taps and the center, the first level keeping only light above the threshold with a soft knee) and back up with additive blending (`PSBloomUp`, eight taps). Then `PSUber` ({engine}`engine/shaders/Post.hlsl`) draws one triangle into the back buffer over the scene viewport: FXAA on the HDR values (edges found on Reinhard-compressed luminance, blended compressed so bright points do not smear), chromatic aberration, exposure × the player's brightness, bloom, AgX (Wrensch's polynomial fit), the color LUT, vignette, film grain and a ±0.5/255 dither. Its 96-byte constants are written into the upload ring. With `toneMapping` off (probe baking) or a debug view it only clamps and encodes sRGB.

A LUT is 32³ cells stored as a 1024 × 32 RGBA8 strip (blue slices side by side); the shader blends two slices. `asset::parseCubeLut` resamples any 3D `.cube` to 32 points (trilinear, honoring `DOMAIN_MIN`/`MAX`), `Renderer::createLut` keeps the cells on the CPU, and the color-blind setting (`PostOptions::colorBlind`, Machado 2009 simulation + daltonize) is applied to every cell when the texture is uploaded, so it costs nothing in the shader. LUT 0 is the identity, used when only the color-blind mode is on.

## Offscreen targets

`rhi::RenderTarget` is a target drawn outside the back buffer; `rhi::TargetKind` picks its formats: `Scene` (HDR color + depth, the scene pipelines), `Hdr` (HDR color only, bloom) or `Ldr` (8-bit color in the back buffer's format, drawn by `Target::Overlay` pipelines and read as sRGB values, so its bytes can be shown in the debug UI as they are). In DX12 each target has a color resource with a render target view and a shader resource view in the bindless heap; in Vulkan it is one image drawn with dynamic rendering, returned to `SHADER_READ_ONLY_OPTIMAL` by `endTarget`. `beginTarget` without a clear color keeps the contents (bloom adds onto them). `Device::destroyRenderTarget` waits for the GPU and frees a target; the renderer uses it only for its window-sized targets.

`Renderer::createRenderTarget` makes an `Ldr` target with a same-sized HDR scene target as its pair. `Renderer::drawToTarget(target, params, drawList, lightingModel)` draws a draw list into the pair after the main 3D and before the UI and runs post processing into the `Ldr` target: it writes another set of frame constants (the material table is written once per frame), swaps the frustum and the lighting model, draws, and puts them back. The editor's look dev window, probe baking and the grading capture use it, and `rhi::imguiTextureId` gives the value `ImGui::Image` needs (a GPU descriptor in DX12, a descriptor set made once per texture in Vulkan).

## Screenshots

`requestCapture(path)` marks the next frame. In `Device::endFrame` the back buffer is copied into a readback buffer (layout from `GetCopyableFootprints`). After presenting, the device waits for that frame's fence and returns the RGBA pixels; the renderer writes the PNG with the platform layer's `savePng`.
The game uses it for `F12` (`screenshot.png`) and for automatic captures in tests.

## Debug views and GPU capture

`FrameParams::debugView` (`render::DebugView`) is passed to `Forward.hlsl` in the push constants (`debugView`, the former padding). The pixel shader returns the normal, a LOD color (instance flag bits 8 to 9), a budget color (flag `kInstanceOverBudget`) or a material feature color (outline red, wind green, rim blue, dissolve yellow, added together) instead of the lit color. View modes use the `Pbr` shader whatever the lighting model, and skip the outline pass.
Two more pipelines from the same shaders are created in builds with the debug UI: wireframe (`PipelineDesc::wireframe`; Vulkan needs the `fillModeNonSolid` feature, which the device enables when present) and overdraw (`additiveBlend`, `depthTest = false`, cleared to black). The editor fills the instance flags in `buildSceneView` only while a view mode is on.

`rhi/GpuCapture.cpp` loads `renderdoc.dll` from `%ProgramFiles%\RenderDoc` (header `third_party/renderdoc/renderdoc_app.h`) or the newest `WinPixGpuCapturer.dll` under `%ProgramFiles%\Microsoft PIX` before the device is created (`DeviceDesc::gpuCapture`), because both tools hook the graphics API at device creation.
`captureNextGpuFrame` calls RenderDoc's `TriggerCapture` and opens its window, or PIX's `PIXGpuCaptureNextFrames`. `--gpu-capture-at <frame>` captures without opening a window (used by `check.ps1`). The PIX path is written but has not been tried with PIX yet.

## Statistics

`RenderStats` holds `drawCalls`, `instances` and `culled`. `beginFrame` resets them, every `drawInstances` adds one draw call and its instance count, and `drawUi` adds one draw call.
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
| HDR scene target | `Renderer::Impl::mainChain`, `Post.hlsl` | 3D is drawn in linear HDR (R11G11B10F, 4 bytes a pixel) and one full-screen pass tone maps it into the back buffer, writing sRGB values. UI and ImGui write sRGB colors onto the same back buffer view. |
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
