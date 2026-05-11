# envault

A minimal secrets manager that syncs environment variables from AWS SSM Parameter Store into local `.env` files for dev workflows.

---

## Installation

```bash
pip install envault
```

Or with pipx for isolated installs:

```bash
pipx install envault
```

---

## Usage

Pull parameters from a given SSM path prefix and write them to a local `.env` file:

```bash
envault pull --path /myapp/dev --output .env
```

This will fetch all parameters under `/myapp/dev/*` from AWS SSM Parameter Store and write them as key-value pairs into `.env`:

```
DB_HOST=localhost
DB_PASSWORD=supersecret
API_KEY=abc123
```

You can also specify a named AWS profile:

```bash
envault pull --path /myapp/prod --output .env.prod --profile my-aws-profile
```

Push local `.env` values back up to SSM:

```bash
envault push --path /myapp/dev --input .env
```

> **Note:** envault uses your existing AWS credentials. Make sure your environment has valid credentials configured via `~/.aws/credentials`, environment variables, or an IAM role.

---

## Requirements

- Python 3.8+
- AWS credentials with `ssm:GetParametersByPath` and `ssm:PutParameter` permissions

---

## License

MIT © [envault contributors](https://github.com/yourname/envault)