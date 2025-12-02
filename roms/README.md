# Pokemon ROMs

This directory contains Pokemon ROM files for the Pokemon LLM project.

## Supported ROM Files

### Generation 1 (.gbc)
- Pokemon Red (red.gbc)
- Pokemon Blue (blue.gbc)
- Pokemon Yellow (yellow.gbc)

### Generation 2 (.gbc)
- Pokemon Gold (gold.gbc)
- Pokemon Silver (silver.gbc)
- Pokemon Crystal (crystal.gbc)

### Generation 3 (.gba) - Recommended
- Pokemon FireRed (firered.gba) - **Default**
- Pokemon LeafGreen (leafgreen.gba)

## Configuration

ROM files are configured via the `POKEMON_ROM` environment variable:

```bash
# Default looks for roms/firered.gba
POKEMON_ROM=firered.gba

# You can also specify subdirectories or absolute paths
POKEMON_ROM=subfolder/special-version.gba
POKEMON_ROM=/path/to/my/roms/firered.gba
```

## Current Support Status

- ✅ **Generation 1**: Fully supported
- 🚧 **Generation 2**: Planned support
- 🚧 **Generation 3**: FireRed/LeafGreen in development

## Legal Notice

- Only use ROM files that you legally own
- Dump your own game cartridges when possible
- Respect copyright laws in your jurisdiction