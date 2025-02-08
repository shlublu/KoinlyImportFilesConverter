# KoinlyImportFilesConverter
- Converts history files from various CEX and block explorers to Koinly import files.
- Displays the balance changes engendered by these generated Koinly import files.

## Usage
- `koinly_convert.py meria|etherlink path/to/file.csv [path/to/etherlink_tokens_transfer_file.csv (Etherlink only)]`
    - Meria input files should be generated as 'WaltioCSV' files from https://www.meria.com 
    - Etherlink input files should be generated from https://explorer.etherlink.com

- `koinly_check.py path/to/file.csv`
    - The input file should be a Koinly import file generated with `koinly_convert.py`

## Disclaimer
I built this tool for my own use, and I apologize as it looks a bit quick'n'dirty. 
I am sharing it because if it was useful to me, it might be useful to others. However, it comes with no guarantee of any kind.

## Default fiat currency notice
The default fiat currency is EUR. Please adjust the variable 'FIAT_BASE_CURRENCY' to use it with another base currency. 

## Licence
EUPL 1.2 https://joinup.ec.europa.eu/sites/default/files/custom-page/attachment/2020-03/EUPL-1.2%20EN.txt

## Author
Vincent Poulain, 2022-2025
