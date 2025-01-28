

# Ban List Cron
==========================

## Overview
------------

This project is a Python-based script that fetches the security ban list from the National Stock Exchange of India (NSE) and sends it to a Zoho Cliq bot and channel. The script is designed to run daily, skipping holidays, and uses a GitHub Actions workflow to automate the process.

## Requirements
---------------

* Python 3.9+
* `requests` library
* `certifi` library
* `charset-normalizer` library
* `idna` library
* `urllib3` library
* Zoho OAuth token (provided via GitHub Secrets)
* Zoho Cliq bot and channel setup

## Setup
--------

1. Clone the repository to your local machine.
2. Create a new file named `requirements.txt` and add the required libraries.
3. Install the required libraries using `pip install -r requirements.txt`.
4. Set up your Zoho OAuth token as a GitHub Secret named `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REDIRECT_URI`, and `ZOHO_REFRESH_TOKEN`.
5. Set up your Zoho Cliq bot and channel.

## Usage
-----

1. Run the script using `python main.py`.
2. The script will fetch the security ban list from the NSE and send it to the Zoho Cliq bot and channel.

## GitHub Actions Workflow
---------------------------

The project uses a GitHub Actions workflow to automate the script execution. The workflow is triggered daily at 9:00 AM UTC and runs the script using the `main.py` file.

## Files
------

* `zohotok.py`: A Python module that generates an access token using the refresh token.
* `main.py`: The main script that fetches the security ban list and sends it to the Zoho Cliq bot and channel.
* `requirements.txt`: A file that lists the required libraries.
* `.github/workflows/run_main.yml`: The GitHub Actions workflow file.

## Troubleshooting
-----------------

* Check the logs for any errors or issues.
* Verify that the Zoho OAuth token is set up correctly.
* Verify that the Zoho Cliq bot and channel are set up correctly.

## License
-------

This project is licensed under the MIT License.

You can copy and paste this content into your README file, and it should maintain the proper formatting.
