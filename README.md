# Image_2_ASCII

**An Open-Source command-line tool for converting images into ASCII representation** 
 
## Disclaimer

- **⚠︎ This project is under development!**
- **⚠︎ Expect bugs and breaking changes.**
  
 This source code is licensed under the BSD-style license found in the **[LICENSE](LICENSE)** file in the root directory of this Repository.

## How to run

You will need the packages mentioned in [requirements.txt](requirements.txt) in order to run this app. **If you already have the required packages, you can skip this section.** Otherwise, you can install them by running the following shell command
```sh
$ pip install -r requirements.txt
```

or if you want to setup a **virtual** enviroment to not pollute the **root** enviroment, you can run one of the following commands, depending on your Operating System.

First, create the virtual enviroment

```sh
$ python -m venv venv/<name>
```
then, activate it using the appropriate command, depending on your OS.

##### Windows
```sh
$ ./venv/<name>/Scripts/Activate
```

##### Linux
```sh
$ source venv/<name>/bin/activate
```

\
When thats completed, run the shell command
```sh
$ pip install -r requirements.txt
```

## Usage

This tool has a few features executed via command-line flags. In its simplest form, it analyses an image and splits it into a 2-Dimensional grid to then convert each slot into a grayscale format and assign an ASCII character to it from a given range.
You can always run the tool with the flag `-h` for info about each flag.

``` title="Usage command"
converter.py inputFile [-h] [-a] [-c]
                       [-wi INTEGER | -wc INTEGER]
                       [-hi INTEGER | -hc INTEGER]
                       [-gsc {10,70} (def: 70)]
                       [-op PATH] [-t {txt, svg, png, jpg, xml} (def: txt)]
```

### Explanation of the flags

| Flag   | Long Flag          | Description                                                                             | Value type                | Implemented |
| :----- | :----------------- | :-------------------------------------------------------------------------------------- | :------------------------ | :---------: |
| `-h`   | `--help`           | Displays a help message with more info.                                                 | Bool                      |      ✔      |
| `-a`   | `--auto`           | Figures out the usage parameters automatically from the input                           | Bool                      |      ✖      |
| `-c`   | `--colored`        | Output text will be colored instead of grayscale. Used for XML or image output formats. | Bool                      |      ✖      |
| `-wi`  | `--width`          | Custom tile Width in pixels.                                                            | Integer                   |      ✔      |
| `-wc`  | `--widthcount`     | Custom tile amount on the Vertical axis (width).                                        | Integer                   |      ✔      |
| `-hi`  | `--height`         | Custom tile Height in pixels.                                                           | Integer                   |      ✔      |
| `-hc`  | `--heightcount`    | Custom tile amount on the Horizontal axis (height).                                     | Integer                   |      ✔      |
| `-gsc` | `--grayscalecount` | Amount of descrete grayscale values. Currently possible values are 10 and 70.           | [10, 70]                  |    **~**    |
| `-op`  | `--outputfilepath` | The relative path of the output file                                                    | Path                      |      ✔      |
| `-ot`  | `--outputfiletype` | The format of the output file                                                           | [txt, jpg, png, xml, svg] |      ✔      |
| `-on`  | `--name`           | The name method to use for the output file                                              | [CUSTOM, INPUT, RANDOM]   |      ✔      |

## Roadmap

Most recently Done:
- [x] Output file is being saved into path with custom name.
- [x] Separate and Abstract the conversion logic and input/output controller. 
 
Currently doing:
- [ ] Publish a release and set up the semver and the tags.
- [ ] Implement currently partial (**~**) or unimplemented (✖) features.

ToDo List:
- [ ] Allow conversion to pixelart.
- [ ] Allow for custom Grayscale array.
- [ ] Add examples to the readme and improve its visual aspect.
- [ ] Implement edge detection for better results.
- [ ] Add slope support for grayscale-value control.
- [ ] Add other types of characters, like braille for more blocky looks.


## Contribution

Found a bug? Or do you want to help improve this tool? Then please feel free to open a new **Issue** or submit a **Pull Request**!

> [!Important]
> Before you contribute read [CONTRIBUTING.md](CONTRIBUTING.md)

## Donate ♡
If you like this tool or the things I'm creating, please consider **Donating** using the **Kofi** link below or the link on the "Sponsor this project" section! This is NOT mandatory, but it helps out a lot and is greatly appreciated! **:)**\
You will also be added into my **Donation List** for everyone to see! (still in the works)\
(In case you choose to not have your username publicly displayed in the list mentioned above, please email me explicitly saying so in the email address linked in my profile, or saying so in the donation message.)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/R6R7ZBM56)



