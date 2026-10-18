# Requirements

## Running

- Windows 10 1803 or later.
- **Intel 11th generation (Xe) integrated graphics or better**: Direct3D 12 with Shader Model 6.6 and resource binding tier 3. The game checks this at startup and, if the GPU falls short, exits with the reason and the driver version. Bindless resources (Shader Model 6.6) are used from the texture work onward.
- A CPU with SSE4.2.

The reasons for the minimum spec are in the {engine}`decision log <docs/DECISIONS.md>`. `sandbox.exe --system-info` prints the CPU and GPU features and exits with code 2 below the minimum spec.

## Building

- Visual Studio 2022 or Build Tools 2022 with the "Desktop development with C++" workload (includes CMake).
- Python 3, only to regenerate the sample models.
- For the `ClangCL` comparison build: the Visual Studio component "C++ Clang tools for Windows".
