# Building the engine

Run these from the engine folder (the engine repository):

```bat
build.bat Editor     :: general-purpose editor: build\Editor\bin\MealKitEditor.exe + mealkit.dll + sandbox_game.dll
build.bat            :: Release: build\Release\bin\sandbox.exe (shipped game, engine linked statically) + sandbox_headless.exe (simulation without a window)
build.bat Debug      :: Debug (the D3D12 debug layer is turned on automatically)
build.bat Profile    :: Release + Tracy profiling
build.bat Export     :: release folder export\sandbox\
build.bat ClangCL    :: clang-cl Release: build\ClangCL\bin (to compare determinism with the MSVC build, not shipped)
```

`build.bat` calls `tools\build_project.bat`, which loads the Visual Studio environment (vcvars64) and builds with Ninja into `build\<Config>`.
`ClangCL` needs the Visual Studio component "C++ Clang tools for Windows" (clang-cl on PATH; otherwise it is looked up in Visual Studio installations, preview versions included).

Each game project has its own `build.bat` that takes the same arguments (its build folder is `build\` inside the project). A project's `build.bat Editor` builds only the game DLL, and builds the engine editor first if it is out of date.
Close the editor before rebuilding the engine (`mealkit.dll`): while it runs, the file is locked and linking fails. The game DLL can be rebuilt with the editor open.

To open the editor after building, see {doc}`first_project`.
