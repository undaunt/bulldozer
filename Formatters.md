# Formatters
There are a number of formatters that can be used to format data. You attach the formatters to any given API or scraper, and they will be automatically transformed.

All formatters share these common settings:
- **property**: The property in the data to format (e.g., `description`).
- **method**: The method used for formatting. See the available methods below.
- **settings**: The settings to use for the formatter. See each formatter for available settings.

## Methods

### Max line length
**method**: limit_line_length

Available settings
- **max_length**: The maximum length of a line before it gets wrapped (default is 125 characters).

### Conditional Data
**method**: conditional_data

Available settings
- **property**: The new property to set based on the condition (e.g., `author_article`).
- **condition**: The type of condition to check (e.g., `regex`).
- **condition_value**: The regex pattern to match against the property value.
- **if_true**: The value to set if the condition is met (e.g., `An`).
- **if_false**: The value to set if the condition is not met (e.g., `A`).
- **overwrite**: Whether to overwrite any existing property value (default is `false`).

Available conditions:
- **regex**: Use regex to check the if **condition_value** is true or false

### Replacer
**method**: replacer

Available settings
- **replacements**: A collection of pattern replacements to perform, should consist of:
  - **pattern**: What to look for (e.g., '(?<=\.)(?! )').
  - **replacement**: What to replace it with (e.g., '\n').
