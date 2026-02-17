# Data Contract (v1)

## Canonical payload

```json
{
  "schema_version": "v1",
  "as_of_utc": "2026-02-16T23:00:00Z",
  "trade_date": "2026-02-13",
  "fed": {
    "effective_fed_funds_rate": 3.64,
    "target_lower": 3.50,
    "target_upper": 3.75,
    "source": []
  },
  "tsp": {
    "funds": {
      "C": 109.5106,
      "S": 103.8681,
      "I": 60.8406,
      "G": 19.6894,
      "F": 21.1707
    },
    "source": "",
    "note": ""
  },
  "meta": {
    "producer": "moose-core",
    "checksum_sha256": "optional"
  }
}
```

## Rules
- `schema_version` required
- `trade_date` in `YYYY-MM-DD`
- prices/rates are numeric or `null`
- source URLs required for every dataset
