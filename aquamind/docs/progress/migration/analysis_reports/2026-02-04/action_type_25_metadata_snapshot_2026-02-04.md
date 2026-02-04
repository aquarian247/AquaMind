# ActionType 25 Metadata Snapshot

Date: 2026-02-04
Source: `ActionMetaData` joined to `Action` where `ActionType = 25`

## Top ParameterID / ParameterString pairs

| ParameterID | ParameterString | Count |
|---|---|---|
| 327 | NULL | 252,788 |
| 18 | NULL | 197,598 |
| 1 | NULL | 165,754 |
| 2 | NULL | 112,443 |
| 344 | `<S></S>` | 78,321 |
| 66 | NULL | 67,129 |
| 119 | `<SD><SC>8</SC><MG>0</MG><CD>false</CD></SD>` | 52,734 |
| 119 | `<SD><SC>5</SC><MG>0</MG><CD>False</CD><ST>4</ST><PC>...` | 4,455 |
| 351 | NULL | 1,977 |
| 12 | NULL | 1,135 |
| 10 | NULL | 1,032 |
| 11 | NULL | 877 |

Notes
- `ParameterString` is often NULL or structured XML-like payloads (likely sample data packets).
- These metadata fields are not obviously keyed to fish counts or population IDs without additional decoding.

