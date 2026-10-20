# MealKit documentation

MealKit is a lightweight **3D multiplayer game engine** that runs fast even on office PCs with Intel integrated graphics.
Today it targets Windows and DirectX 12. Other platforms come in stage 5 of the roadmap.

This documentation is written in English and translated into Korean. Rules that change together with engine code
(the coding model, the determinism rules, the external library table) live in the engine repository, and these pages link to them.

The documentation has two parts:

- **Game developer guide**: making a game with MealKit. Start with {doc}`getting_started/index`, then look up topics in the {doc}`manual/index`.
- **Engine developer guide**: working on the engine and the editor themselves. Start with {doc}`engine_dev/index`, then read {doc}`engine_dev/internals/index` folder by folder.

```{toctree}
:maxdepth: 2
:caption: About

about/introduction
about/requirements
about/license
```

```{toctree}
:maxdepth: 2
:caption: Game developer guide

getting_started/index
manual/index
cookbook/index
reference/index
```

```{toctree}
:maxdepth: 2
:caption: Engine developer guide

engine_dev/index
engine_dev/internals/index
```
