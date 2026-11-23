# SpiderNet V2 (OSintSPIdernet)

> **Status:** Work in Progress (functional core CLI; additional platforms, error handling, and reporting features are still in development).
>
> **Disclaimer:** This is an educational project built to practice Python automation, HTTP request handling, and authorized OSINT techniques. Only use it on public information you are legally allowed to query.

Command-line OSINT tool written in Python that enumerates public user profiles across 34 platforms and recursively crawls discovered social links, displaying structured results in the terminal with `Rich`.

## Features

- **Multi-platform enumeration:** Checks username presence across 34 supported public platforms.
- **Recursive social link crawling:** Extracts and follows related social profile links found during enumeration.
- **Request management:** Includes User-Agent rotation and cookie persistence across requests.
- **Clean terminal UI:** Uses `Rich` for structured, readable console output.

## Requirements

- **Python 3.9 or higher** (`python --version`)

## Installation

1. Clone the repository:

```bash
git clone [https://github.com/dipargu/OSintSPIdernet.git](https://github.com/dipargu/OSintSPIdernet.git)
cd OSintSPIdernet
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
```

- **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
- **Windows (CMD):** `venv\Scripts\activate.bat`
- **Linux / macOS:** `source venv/bin/activate`

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the tool from the terminal:

```bash
python main.py
```

## Planned Improvements

- Export results to JSON / CSV reports.
- Improve rate-limit handling and retry logic.
- Expand platform coverage and reduce false positives.
