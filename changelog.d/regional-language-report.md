### Fixed

- **The training report and Assist speak a regional language of Home Assistant:** the ready-made `summary` of the training report now comes in the language of Home Assistant, such as "30 Darts, 3-Dart-Average 57,3, höchste Aufnahme 140, 1 × 180." in German, from the new `summary` attribute of the *Training darts* sensor; an automation made from the blueprint gets it with the update. Assist answers in German, Spanish, French or Dutch also when Home Assistant speaks a regional variant such as `de-CH` or `es-419`, with the name of the game in that language too, instead of in English.
