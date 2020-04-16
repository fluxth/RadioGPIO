# RadioGPIO
Simple, lightweight and robust GPIO client and server for radio facilities.

[Donate Link Here]

[Screenshot here]


Features
------

* Very high stability

---


**Important remarks!**
------

**Please acknowledge the following before you continue:**

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

_Therefore, please, test this software and its configuration throughly in a controlled off-air environment **before** deploying this to your live ON-AIR system._

Installation
------

There are 2 main ways of installing RadioGPIO on your system, choose your flavor:

### 1. The Easy Way: **Installer package**
  - Simple installer wizard, recommended for most users. 
  - Go to the [release section](#releases), download and install the latest version, and you're up and running.

### 2. Enter the rabbit-hole: **Run from existing Python installation / Build from source**
  - You may need to modify the source code to meet your needs. In that case, you'll need a Python 3.8 environment installed with the modules listed in `requirements.txt`.
  - Manually building an installer will require `pyinstaller` package and InnoSetup installed on your build system.
  - Do a `git clone https://github.com/fluxTH/RadioGPIO` and mod away!

Latest release
------

You can download the latest version of RadioGPIO by [visiting the releases page]().

Configuration
------

A configuration file named `config.json` should be present alongside the application executable at runtime. In the case that the configuration file is not found, the application will create a default one for you. Use your favorite text editor to modify its contents to your need. _(Editors with JSONLint feature are strongly recommended)_

You can copy the configured `config.json` file and drop it into any system running the same RadioGPIO version, all its configurations will be carried with it.

Here's an overview of what you'll see in the `config.json` file, *note that blocks with `...` is shortened*:

```
{
    "System": { ... },
    "Interface": { ... },
    "Actions": [ ... ],
    "Modules": { ... }
}
```

There are 4 main parts to the configuration file:

- `System` - [Application configuration](#config-system)
- `Interface` - [User interface configuration](#config-interface)
- `Actions` - [Action definiton block](#config-actions)
- `Modules` - [Modules configuration](#config-modules)

### 1. `System` - Application configuration

This part of the confiuration 

### 2. `Interface` - User interface configuration

### 3. `Actions` - Action definiton block

This part of the confiuration defines your ___action___ that will be used when you run RadioGPIO. Here's an example of what an **action definition** can look like:

```
"Actions": [
    {
        "Name": "action_sw_pgm",
        "Text": "Switch feed to PGM",
        "Sequence": [
            {
                "Type": "RunOutputCommand",
                "Module": "HTTPClient",
                "OutputCommand": "httpout_sw_pgm"
            },
            {
                "Type": "RunOutputCommand",
                "Module": "HTTPClient",
                "OutputCommand": "httpout_fm_stereo",
                "Delay": 0.9
            }
        ]
    },
    { ... }
]
```

### 4. `Modules` - Modules configuration


Usage
------

Run the program

Taskbar

Licensing
------

This software is released under the GNU-GPLv3 license. Some parts of the software are released under other licenses as specified.

This software contains code from [`Livewire-Routing-Protocol-Client` by anthonyeden](https://github.com/anthonyeden/Livewire-Routing-Protocol-Client) under the GNU-GPLv2 license.

Support the developers
------

