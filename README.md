![DataTractor logo](logo.png)

# DataTractor

![](https://img.shields.io/badge/python%20version-3.6-blue.svg)

Extract game data from web sources.

## How to use

### Setup & Run
You need python version 3. To install the package, run:
```bash
python setup.py install
```
Tip: you can add the `--user` option to install it for you only, without root permissions.

Then, in the repo's main directory, simply run the `xtract` script:

```bash
python xtract.py -v game_version -o output_directory
```

`-o` might be omitted, see below.

### Options

| Type | Option | Description |
| ---- | ------ | ----------- |
| Mandatory | `-v version` | Sets the game version |
| Optional | `-o dir` | Sets the output directory, default is `./out/generated_$v` where `$v` is the game version |
| Optional | `-p` or `--packets` | Enables the packets extractor |
| Optional | `-b` or `--blocks` | Enables the blocks extractor |
| Optional | `--nocache` | Disables the HTTP cache |
| Optional | `--cachetime seconds` | Sets the cache timeout in seconds, default is 300s (5 minutes) |

If no extractor is specified, all the available extractors will run.

### Example

```bash
python xtract.py -v 1.12.2 --packets
```
This will generate all the packets classes for Minecraft version `1.12.2`.
