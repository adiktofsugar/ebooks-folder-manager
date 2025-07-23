# Pyright Type Checking Analysis

## Summary
This analysis was performed to identify common pyright warnings in the codebase that may not be useful and could be disabled in the configuration.

## Current Pyright Ignore Comments in Code
Found 2 explicit pyright ignore comments:
- `efm/detection.py:35` - `pyright: ignore[reportUnknownMemberType]`
- `efm/cover.py:57` - `pyright: ignore[reportInvalidCast]`

## Frequency of Pyright Warning Types
Analysis of all pyright warnings in the codebase:

| Warning Type | Count | Description |
|-------------|-------|-------------|
| reportUnknownMemberType | 170 | Member access on values with unknown types (usually from external libraries) |
| reportUnknownArgumentType | 148 | Function arguments with unknown types |
| reportAny | 128 | Use of `Any` type (often from yaml.safe_load, json.loads) |
| reportUnknownParameterType | 67 | Function parameters with unknown types |
| reportMissingParameterType | 63 | Missing type annotations on function parameters |
| reportDeprecated | 17 | Use of deprecated features |
| reportUnusedParameter | 8 | Unused function parameters |
| reportCallIssue | 4 | Issues with function calls |
| reportOperatorIssue | 2 | Type incompatibility with operators |
| Others | <5 each | Various other warnings |

## Recommendation
The top warnings are mostly related to:
1. **Third-party library types** - PyMuPDF, ebooklib, and other libraries don't provide complete type information
2. **Dynamic data** - YAML/JSON parsing returns Any types
3. **Missing annotations** - Some functions lack type annotations

These warnings don't indicate actual bugs but rather incomplete type information. Consider adding these to `pyrightconfig.json`:

```json
{
  "reportUnknownMemberType": false,
  "reportUnknownArgumentType": false,
  "reportAny": false,
  "reportUnknownParameterType": false,
  "reportMissingParameterType": false,
  "reportDeprecated": false
}
```

## Remaining Critical Issues
After disabling the above, focus on fixing:
- Bare except statements (E722) - These have been fixed
- Unused variables/imports (F841, F401) - Most have been fixed
- Actual type errors (reportCallIssue, reportOperatorIssue) - These may indicate real bugs

## Notes
- Total warnings: ~615 (mostly type-related) - reduced from ~630 after fixing implicit overrides
- Total errors: ~13 (mostly in external DeDRM_tools)
- The codebase would benefit from type stubs for PyMuPDF and other external libraries
- reportImplicitOverride warnings have been fixed by adding @override decorators where needed