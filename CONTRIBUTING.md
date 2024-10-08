# How to contribute to this project

**Follow the [style guide](#style) and try to stick to a similar coding style as the project has**.

**Prefer to stick to current issues, the road map and todo list**. 
[Here](#where-is-the-todo-list-and-roadmap) you can find out how to find them.

Each pull request should **stick to a single problem or feature to add**, do not mix them into the same.
**Bug fixes may contain multiple** bug fixes in the same pull request as it is considered similar. 

On **bug fixes** create a **patch note in the pull request message** so we know which bugs has been patched.

> [!Note]
> Use type hints

> [!Important]
> If you are fulfilling an issue refer to that issue number in the commits or pull request message

## Style

### Rules

- Keep to a **line width of 120**

- On **bigger scope bodies** use **2 lines to next definition**
```python
def simpleBody():
    return "Foo"

def largeBody():
    if condition:
        x = "Bar"
    else:
        x = "Baz"

    print(x)


def next():
    ...
```

### Casing

| Kind                      | Case          |
| :------------------------ | :------------ |
| **Class**                 | ClassName     |
| **Private Class**         | PClassName    |
| **Class Fields**          | fieldName     |
| **Class Methods**         | methodName    |
| **Private Class Fields**  | pFieldName    |
| **Private Class Methods** | pMethodName   |
| **Enum**                  | EnumName      |
| **Enum Fields**           | EnumField     |
| **Enum Methods**          | enumMethod    |
| **Enum Private Methods**  | pEnumMethod   |
| **Function**              | functionName  |
| **Private Function**      | pFunctionName |
| **Variable**              | variableName  |
| **Const Variable**        | VARIABLE_NAME |
| **Private Variable**      | pVariableName |
| **Module**                | fileName      |
| **Private Module**        | pfileName     |

### TODO

**There are several ways to write todo's in this codebase, these are as follows:**

| Syntax             | Description                                             |
| :----------------- | :------------------------------------------------------ |
| `FIXME: <message>` | Used when there is a issue in the typing or in the code |
| `HACK: <message>`  | Used when you have created a hotfix for a bug           |
| `TODO: <message>`  | Used for any todo that does not fit in any of the above |

## Where is the Todo list and Roadmap?

### Roadmap

The roadmap can be found in the top level readme file of the project, this includes a todo list aswell.

### Todo list

**There are several places to find the todo lists:**

1. [Top level Readme](README.md) under Roadmap
2. [Readme inside src/](src/README.md) under TODOs
3. there are [TODOs](#todo) scattered in the codebase, these can be found with your favorite search tool

## Dependencies

All dependencies has to be **added into [requirements.txt](requirements.txt)** on the top level.

If you are **creating a virtual environment (.venv)** 
put it in any of the folders currently in [.gitignore](.gitignore) found **under the Environments comment**.

> [!Important]
> Ask before you add any dependecies
