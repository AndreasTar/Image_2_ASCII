# Image_2_ASCII
**A command-line tool for converting images into ASCII representation** 
 
## Disclaimer
- **⚠︎ This project is under development!**
- **⚠︎ Expect bugs and breaking changes.**
  
 This source code is licensed under the BSD-style license found in the **LICENSE** file in the root directory of this Repository.

## Usage
This tool has a few features executed via command-line flags. In its simplest form, it analyses an image and splits it into a 2-Dimensional grid to then convert each slot into a grayscale format and assign an ASCII character to it from a given range.
You can always run the tool with the flag `-h` for info about each flag.

``` title="Usage command"
converter.py inputFile [-h] [-a] [-c]
                       [-wi INTEGER | -wc INTEGER]
                       [-hi INTEGER | -hc INTEGER]
                       [-gsc {10,70} def: 70]
                       [-op PATH] [-t {png, jpg, xml, txt} def: txt]
```

### Explanation of the flags

| Flag                        | Description                                                                             | Value type           | Implemented |
| :-------------------------- | :-------------------------------------------------------------------------------------- | :------------------- | :---: |
| `-h` / `--help`             | Displays a help message with more info.                                                 | Bool                 |   ✔  |
| `-a` / `--auto`             | Figures out the usage parameters automatically from the input                           | Bool                 |   ✖  |
| `-c` / `--colored`          | Output text will be colored instead of grayscale. Used for XML or image output formats. | Bool                 |   ✖  |
| `-wi` / `--width`           | Custom tile Width in pixels.                                                            | Integer              |   ✔  |
| `-wc` / `--widthcount`      | Custom tile amount on the Vertical axis (width).                                        | Integer              |   ✔  |
| `-hi` / `--height`          | Custom tile Height in pixels.                                                           | Integer              |   ✔  |
| `-hc` / `--heightcount`     | Custom tile amount on the Horizontal axis (height).                                     | Integer              |   ✔  |
| `-gsc` / `--grayscalecount` | Amount of descrete grayscale values. Currently possible values are 10 and 70.           | [10, 70]             | **~** |
| `-op` / `--outputfilepath`  | The relative path of the output file                                                    | Path                 |   ✔  |
| `-t` / `--outputfiletype`   | The format of the output file                                                           | [txt, jpg, png, xml] | **~** |

## Roadmap

Done:
- [x] Output file is being saved into path with custom name.
 
Currently doing:
- [ ] Separate and Abstract the conversion logic and input/output controller.

ToDo List:
- [ ] Implement currently partial (**~**) or unimplemented (✖) features.
- [ ] Implement edge detection for better results.
- [ ] Add slope support for grayscale-value control.
- [ ] Add examples to the readme and improve its visual aspect.
- [ ] Add other types of characters, like braille for more blocky looks.
- [ ] Allow for custom Grayscale array.


## Contribution
Found a bug? Or do you want to help improve this tool? Then please feel free to open a new **Issue** or submit a **Pull Request**!

## Donate ♡
If you like this tool or the things I'm creating, please consider **Donating** using the **Kofi** link below! This is NOT mandatory, but it helps out a lot and is greatly appreciated! **:)**\
You will also be added into my **Donation List** for everyone to see! (still in the works)\
(In case you choose to not have your username publicly displayed in the list mentioned above, please email me explicitly saying so in the email address linked in my profile, or saying so in the donation message.)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/R6R7ZBM56)



