# KoinlyImportFilesConverter
Converts history files from various CEX to Koinly import files.

## Usage
`koinly_convert.py binance_card|meria|ftx_deposits|ftx_conversions|ftx_trades|ftx_withdrawals path/to/file.csv`

## Disclaimer
I built this tool for my own use, and I apologize as it looks a bit quick'n'dirty. 
I am sharing it because if it was useful to me, it might be useful to others. However, it comes with no guarantee of any kind.

## Default fiat currency notice
The default fiat currency is EUR by default. Please adjust the variable 'FIAT_BASE_CURRENCY' below to use it with another base currency. 
This is very important for Binance Card export files as this corresponds to the card's currency. This is expected to be minor for export files from other CEXs.

## Binance card notice
Binance Card history files are provided as Excel files by Binance. They should be converted to CSV files using the Excel's 'Save As' function prior using this tool. 
Koinly Converter uses the CSV delimiter ';' by default. This can be changed by modifying the CSV_DELIMITER_IN_BINANCECARD variable below.

## FTX notice
FTX 'trades' and 'conversions' export files are localized according to the user's language, and this tool has been tested with french files. Please adjust the variables 'FTX_CONVERSIONS_SUCCESS_STATUS' and 'FTX_TRADES_BUY_SIDE' below prior using this tool with files localized otherwise. Appropriate values can be found in the FTX export files themselves.

These variables are tuples, so it is perfectly okay to add values corresponding to your language and to send me a pull request to make this tool better.

## Licence
EUPL 1.2 https://joinup.ec.europa.eu/sites/default/files/custom-page/attachment/2020-03/EUPL-1.2%20EN.txt

## Author
Vincent Poulain, December 2022
