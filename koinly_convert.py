#!/bin/python

'''
Koinly Converter: converts history files from various CEX to Koinly import files.

Usage: koinly_convert.py binance_card|meria|ftx_deposits|ftx_conversions|ftx_trades|ftx_withdrawals path/to/file.csv

Disclaimer: I built this tool for my own use, and I apologize as it looks a bit quick'n'dirty. 
            I am sharing it because if it was useful to me, it might be useful to others. However, it comes with no guarantee of any kind.

Default fiat currency notice: the default fiat currency is EUR. Please adjust the variable 'FIAT_BASE_CURRENCY' below to use it with another base currency. 
                              This is very important for Binance Card export files as this corresponds to the card's currency. This is expected to be minor for export files from other CEXs.

Binance card notice: Binance Card history files are provided as Excel files by Binance. They should be converted to CSV files using the Excel's 'Save As' function prior using this tool. 
                     Koinly Converter uses the CSV delimiter ';' by default. This can be changed by modifying the CSV_DELIMITER_IN_BINANCECARD variable below.

FTX notice: FTX 'trades' and 'conversions' export files are localized according to the user's language, and this tool has been tested with french files. Please adjust the variables
            'FTX_CONVERSIONS_SUCCESS_STATUS' and 'FTX_TRADES_BUY_SIDE' below prior using this tool with files localized otherwise. Appropriate values can be found in the FTX export files themselves.
            These variables are tuples, so it is perfectly okay to add values corresponding to your language and to send me a pull request to make this tool better.

Licence: EUPL 1.2 https://joinup.ec.europa.eu/sites/default/files/custom-page/attachment/2020-03/EUPL-1.2%20EN.txt
Author: Vincent Poulain, December 2022
'''


FIAT_BASE_CURRENCY = 'EUR'

CSV_DELIMITER_OUT = ';'
CSV_DELIMITER_IN_BINANCECARD = ';'

FTX_CONVERSIONS_SUCCESS_STATUS = ('Converti')
FTX_TRADES_BUY_SIDE = ('acheter')


class OutputLine:
    def __init__(
        self, 
        txDate, sentAmount, sentCurrency, receivedAmount, receivedCurrency, *, 
        feeAmount = None, feeCurrency = None, netWorthAmount = None, netWorthCurrency = None, label = None, description = None, txHash = None
        ) -> None:
        self.txDate = txDate
        self.sentAmount = sentAmount
        self.sentCurrency = sentCurrency
        self.receivedAmount = receivedAmount
        self.receivedCurrency = receivedCurrency
        self.feeAmount = feeAmount
        self.feeCurrency = feeCurrency
        self.netWorthAmount = netWorthAmount
        self.networthCurrency = netWorthCurrency
        self.label = label
        self.description = description
        self.txHash = txHash


    def toList(self):
        return [
            self.txDate, 
            self.sentAmount, self.sentCurrency, 
            self.receivedAmount, self.receivedCurrency,
            self.feeAmount, self.feeCurrency,
            self.netWorthAmount, self.networthCurrency,
            self.label,
            self.description,
            self.txHash
        ]


    @staticmethod
    def headers():
        return OutputLine(
            txDate = 'Date', 
            sentAmount = 'Sent Amount', sentCurrency = 'Sent Currency', 
            receivedAmount = 'Received Amount', receivedCurrency = 'Received Currency', 
            feeAmount = 'Fee Amount', feeCurrency = 'Fee Currency', 
            netWorthAmount = 'Net Worth Amount', netWorthCurrency = 'Net Worth Currency',
            label = 'Label', 
            description = 'Description', 
            txHash = 'TxHash'
        )


def doConvert():
    import csv
    import os
    import sys

    MODE_BINANCE_CARD = 'binance_card'
    MODE_FTX_DEPOSITS = 'ftx_deposits'
    MODE_FTX_CONVERSIONS = 'ftx_conversions'
    MODE_FTX_TRADES = 'ftx_trades'
    MODE_FTX_WITHDRAWALS = 'ftx_withdrawals'
    MODE_MERIA = 'meria'

    if len(sys.argv) != 3:
        print(
            f'Usage: {sys.argv[0]} {MODE_BINANCE_CARD}|{MODE_MERIA}|{MODE_FTX_DEPOSITS}|{MODE_FTX_CONVERSIONS}|{MODE_FTX_TRADES}|{MODE_FTX_WITHDRAWALS} path/to/file.csv', 
            file = sys.stderr
        )

    else:
        filePath = sys.argv[2]

        try:
            with open(filePath, newline = '') as inputFile:
                mode = sys.argv[1]
                lines = None

                if mode == MODE_BINANCE_CARD:
                    lines = convertBinanceCard(inputFile)
                elif mode == MODE_FTX_DEPOSITS:
                    lines = convertFtxDeposits(inputFile)
                elif mode == MODE_FTX_CONVERSIONS:
                    lines = convertFtxConversions(inputFile)
                elif mode == MODE_FTX_TRADES:
                    lines = convertFtxTrades(inputFile)
                elif mode == MODE_FTX_WITHDRAWALS:
                    lines = convertFtxWithdrawals(inputFile)
                elif mode == MODE_MERIA:
                    lines = convertMeria(inputFile)
                else:
                    print(f'Unknown mode: {mode}. Try "{sys.argv[0]} help" for help.', file = sys.stderr)

        except FileNotFoundError:
            print(f'Cannot open "{filePath}": file not found.', file = sys.stderr)

        splittedPath = os.path.split(filePath)

        with open(os.path.join(splittedPath[0], f'koinly_{splittedPath[1]}'), mode = 'w', newline = '') as outputFile:
            writer = csv.writer(outputFile, delimiter = CSV_DELIMITER_OUT, quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(OutputLine.headers().toList())
            for row in lines:
                writer.writerow(row.toList())


def csvReader(inputFile, delimiter):
    import csv

    reader = csv.reader(inputFile, delimiter = delimiter)
    next(reader)

    return reader


def convertBinanceCard(inputFile):
    import datetime

    reader = csvReader(inputFile, CSV_DELIMITER_IN_BINANCECARD)
    lines = []

    for row in reader:
        txDate = datetime.datetime.strptime(row[0], '%a %b %d %X %Z %Y').strftime('%Y-%m-%d %X')
        description = row[1]
        paidOutFiat = row[2]
        paidInFiat = row[3]
        feeFiat = row[4]
        assets = [ e.strip().split(' ') for e in row[5].split(CSV_DELIMITER_IN_BINANCECARD) ]
        splits = [ e.strip().split(' = ')[-1].split(' ') for e in row[6].split(CSV_DELIMITER_IN_BINANCECARD) ]

        if not paidInFiat:
            lines.append(
                OutputLine(
                    txDate = txDate, 
                    sentAmount = paidOutFiat, sentCurrency = FIAT_BASE_CURRENCY, 
                    receivedAmount = None, receivedCurrency = None, 
                    feeAmount = None, feeCurrency = None, 
                    label = 'liquidity out', 
                    description = description
                )
            )            
        
            if len(assets) > 1:
                for asset in assets[:-1]:
                    assetCurrency = asset[0]
                    assetAmount = asset[1]

                    if assetCurrency != FIAT_BASE_CURRENCY:
                        cryptoForFiat = float(splits[0][0])
                        receivedAmount = (1.0 / cryptoForFiat) * float(assetAmount)
                        feeAmount = (receivedAmount / float(paidOutFiat)) * float(feeFiat)

                        lines.append(
                            OutputLine(
                                txDate = txDate, 
                                sentAmount = assetAmount, sentCurrency = assetCurrency, 
                                receivedAmount = str(receivedAmount), receivedCurrency = FIAT_BASE_CURRENCY, 
                                feeAmount = str(feeAmount), feeCurrency = FIAT_BASE_CURRENCY, 
                                label = 'swap'
                            )
                        )

                        del splits[0]

                        paidOutFiat = str(float(paidOutFiat) - receivedAmount)
                        feeFiat = str(float(feeFiat) - feeAmount)
                    
                    else:
                        paidOutFiat = str(float(paidOutFiat) - float(assetAmount))

            asset = assets[-1]
            assetCurrency = asset[0]

            if assetCurrency != FIAT_BASE_CURRENCY:
                assetAmount = asset[1]

                lines.append(
                    OutputLine(
                        txDate = txDate, 
                        sentAmount = assetAmount, sentCurrency = assetCurrency, 
                        receivedAmount = paidOutFiat, receivedCurrency = FIAT_BASE_CURRENCY, 
                        feeAmount = feeFiat, feeCurrency = FIAT_BASE_CURRENCY, 
                        label = 'swap'
                    )
                )

        else:
            lines.append(
                OutputLine(
                    txDate = txDate, 
                    sentAmount = None, sentCurrency = None, 
                    receivedAmount = paidInFiat, receivedCurrency = FIAT_BASE_CURRENCY, 
                    feeAmount = feeFiat, feeCurrency = FIAT_BASE_CURRENCY, 
                    label = 'liquidity in', 
                    description = description
                )
            ) 

    return lines


def convertFtxDeposits(inputFile):
    import datetime

    reader = csvReader(inputFile, ',')
    lines = []

    for row in reader:
        txId = row[0]
        txDate = datetime.datetime.strptime(row[1].split('.')[0], '%Y-%m-%dT%X').strftime('%Y-%m-%d %X')
        receivedCurrency = row[2]
        receivedAmount = row[3]
        txStatus = row[4]
        description = row[6]

        if txStatus in('confirmed, complete'):
            lines.append(
                OutputLine(
                    txDate = txDate, 
                    sentAmount = None, sentCurrency = None,
                    receivedAmount = receivedAmount, receivedCurrency = receivedCurrency,
                    label = 'liquidity in' if receivedCurrency == FIAT_BASE_CURRENCY else None,
                    description = description,
                    txHash = txId
                )
            )

    return lines
    

def convertFtxConversions(inputFile):
    import datetime

    reader = csvReader(inputFile, ',')
    lines = []

    normalizeAmount = lambda x : x.replace(',', '.').replace(' ', '')

    for row in reader:
        txDate = datetime.datetime.strptime(row[0], '%d/%m/%Y %X').strftime('%Y-%m-%d %X')
        sentCurrency = row[1]
        receivedCurrency = row[2]
        sentAmount = normalizeAmount(row[3])
        feeAmount = normalizeAmount(row[4])
        receivedAmount = normalizeAmount(row[6].split(' ')[0])
        success = row[7] in FTX_CONVERSIONS_SUCCESS_STATUS

        if success:
            lines.append(
                OutputLine(
                    txDate = txDate,
                    sentAmount = sentAmount, sentCurrency = sentCurrency,
                    receivedAmount = receivedAmount, receivedCurrency = receivedCurrency,
                    feeAmount = feeAmount, feeCurrency = sentCurrency,
                    label = 'swap'
                )
            )

    return lines
    

def convertFtxTrades(inputFile):
    import datetime

    reader = csvReader(inputFile, ',')
    lines = []

    for row in reader:
        txId = row[0]
        txDate = datetime.datetime.strptime(row[1], '%d/%m/%Y %X').strftime('%Y-%m-%d %X')
        pairCurrencies = row[2].split('/')
        sentReceivedIndice = (1, 0) if row[3] in FTX_TRADES_BUY_SIDE else (0, 1)
        pairAmounts = (row[5], row[7])
        feeAmount = row[8]
        feeCurrency = row[9] if len(feeAmount) > 0 else None

        sentAmount = pairAmounts[sentReceivedIndice[0]] 
        sentCurrency = pairCurrencies[sentReceivedIndice[0]] 
        receivedAmount = pairAmounts[sentReceivedIndice[1]] 
        receivedCurrency = pairCurrencies[sentReceivedIndice[1]] 

        lines.append(
            OutputLine(
                txDate = txDate,
                sentAmount = sentAmount, sentCurrency = sentCurrency,
                receivedAmount = receivedAmount, receivedCurrency = receivedCurrency,
                feeAmount = feeAmount, feeCurrency = feeCurrency,
                label = 'swap',
                txHash = txId
            )
        )

    return lines    
    

def convertFtxWithdrawals(inputFile):
    import datetime

    reader = csvReader(inputFile, ',')
    lines = []

    for row in reader:
        txDate = datetime.datetime.strptime(row[0].split('.')[0], '%Y-%m-%dT%X').strftime('%Y-%m-%d %X')
        sentCurrency = row[1]
        sentAmount = row[2]
        destination = row[3]
        success = row[4] == 'complete'
        txId = row[5]
        feeAmount = row[6]
        internalId = row[7]

        if success:
            lines.append(
                OutputLine(
                    txDate = txDate,
                    sentAmount = sentAmount, sentCurrency = sentCurrency,
                    receivedAmount = None, receivedCurrency = None,
                    feeAmount = feeAmount, feeCurrency = sentCurrency,
                    description = f'{destination} {txId}',
                    txHash = internalId
                )
            )       
    
    return lines 


def convertMeria(inputFile):
    import sys

    def unhandledTxInfoForTxTypeError(txType, txInfo):
        print(f'Unhandled txInfo for txType {txType}: {txInfo}.', file = sys.stderr)

    normalizeLunaTicker = lambda ticker : ticker if ticker != 'LUNA' else f'{ticker}2'

    reader = csvReader(inputFile, ';')
    lines = []

    for row in reader:
        txHash = row[0] if row[0] != 'n/a' else None
        txType = row[1]
        sourceAmount = row[2]
        sourceCurrency = row[3]
        destinationAmount = row[4]
        destinationCurrency = row[5]
        address = row[6]
        memo = row[7]
        destinationType = row[8]
        feeMultiplier = float(row[9]) / 100.0
        txInfo = row[10]
        txDate = row[11]

        sentAmount = None
        sentCurrency = None
        receivedAmount = None
        receivedCurrency = None
        feeAmount = None
        feeCurrency = None
        label = None
        description = None

        if txType == 'credit':
            if txInfo in ('airdrop', 'deposit', 'order', 'reward', 'unstaking'):
                receivedAmount = destinationAmount
                receivedCurrency = destinationCurrency

                if feeMultiplier > 0:
                    feeAmount = str(feeMultiplier * float(receivedAmount))
                    feeCurrency = receivedCurrency

                label = (
                    txInfo if txInfo in ('airdrop', 'reward') else 
                        'unstake' if txInfo == 'unstaking' else 
                            'liquidity in' if receivedCurrency == FIAT_BASE_CURRENCY else 
                                None
                )

            else:
                unhandledTxInfoForTxTypeError(txType, txInfo)

        elif txType == 'debit':
            if txInfo in ('masternode', 'order', 'reinvestment', 'staking'):
                sentAmount = sourceAmount
                sentCurrency = sourceCurrency

                if feeMultiplier > 0:
                    feeAmount = str(feeMultiplier * float(sentAmount))
                    feeCurrency = sentCurrency

                label = (
                    'stake' if txInfo in ('masternode', 'reinvestment', 'staking') else 
                        'cost' if txInfo in ('order') else 
                            None
                )             

            else:
                unhandledTxInfoForTxTypeError(txType, txInfo)

        elif txType == 'exchange':
            if txInfo == '':
                sentAmount = sourceAmount
                sentCurrency = sourceCurrency

                receivedAmount = destinationAmount
                receivedCurrency = destinationCurrency

                if feeMultiplier > 0:
                    feeAmount = str(feeMultiplier * float(sentAmount))
                    feeCurrency = sentCurrency

                label = 'swap'

            else:
                unhandledTxInfoForTxTypeError(txType, txInfo)

        elif txType == 'withdraw':
            if txInfo == '':
                sentAmount = sourceAmount
                sentCurrency = sourceCurrency

                if feeMultiplier > 0:
                    feeAmount = str(feeMultiplier * float(sentAmount))
                    feeCurrency = sentCurrency

                description = f'{destinationType} {address} {memo}'
                label = None

            else:
                unhandledTxInfoForTxTypeError(txType, txInfo)

        else:
            print(f'Unhandled txType: {txType}.', file = sys.stderr)

        lines.append(
            OutputLine(
                txDate = txDate,
                sentAmount = sentAmount, sentCurrency = normalizeLunaTicker(sentCurrency),
                receivedAmount = receivedAmount, receivedCurrency = normalizeLunaTicker(receivedCurrency),
                feeAmount = feeAmount, feeCurrency = normalizeLunaTicker(feeCurrency),
                label = label,
                description = description,
                txHash = txHash
            )
        )

    return lines


if __name__ == '__main__':
    doConvert()

