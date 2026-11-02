# Building the engine

Run these from the engine folder (the engine repository):

```bat
build.bat Editor     :: general-purpose editor: build\Editor\bin\MealKitEditor.exe + mealkit.dll + sandbox_game.dll
build.bat            :: Release: build\Release\bin\sandbox.exe (shipped game, engine linked statically) + sandbox_headless.exe (simulation without a window)
build.bat Debug      :: Debug (the D3D12 debug layer is turned on automatically)
build.bat Profile    :: Release + Tracy profiling
build.bat Export     :: release folder export\sandbox\
build.bat ClangCL    :: clang-cl Release: build\ClangCL\bin (to compare determinism with the MSVC build, not shipped)
build.bat Vulkan     :: Release with the Vulkan graphics backend: build\Vulkan\bin (to compare with Direct3D 12, not shipped on Windows)
build.bat VulkanEditor :: the editor with the Vulkan backend: build\VulkanEditor\bin
```

`build.bat` calls `tools\build_project.bat`, which runs the shared build script `tools\build.ps1`: it loads the Visual Studio environment (vcvars64) and builds with Ninja into `build\<Config>`.
On Linux and macOS the same script runs with PowerShell 7 and clang: `pwsh build.ps1 Headless` builds the headless game and the tests (the window, renderer and editor for those systems come later).
`ClangCL` needs the Visual Studio component "C++ Clang tools for Windows" (clang-cl on PATH; otherwise it is looked up in Visual Studio installations, preview versions included).

The first build downloads a pinned version of the DXC shader compiler (about 32 MB, checked against a SHA-256 hash) into `%LOCALAPPDATA%\MealKit\tools`; later builds reuse it. The DXC in the Windows SDK cannot make Vulkan shaders, so it is not used.
Every build compiles each shader for both Direct3D 12 (DXIL) and Vulkan (SPIR-V), so a shader that breaks either backend fails the build. To use another DXC with SPIR-V support, pass `-DMEALKIT_SHADER_DXC=<path to dxc.exe>` to CMake.
The `Vulkan` builds need no Vulkan SDK: the headers are in `third_party`, and the Vulkan loader comes with the GPU driver.

Each game project has its own `build.bat` that takes the same arguments (its build folder is `build\` inside the project). A project's `build.bat Editor` builds only the game DLL, and builds the engine editor first if it is out of date.
Close the editor before rebuilding the engine (`mealkit.dll`): while it runs, the file is locked and linking fails. The game DLL can be rebuilt with the editor open.

To open the editor after building, see {doc}`first_project`.
