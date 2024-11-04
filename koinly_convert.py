#!/bin/python3

'''
Koinly Convert: converts history files from various CEX (to date: Meria, Etherlink) to Koinly import files.

Usage: koinly_convert.py meria|etherlink_xtz|etherlink_tokens path/to/file.csv

Disclaimer: I built this tool for my own use, and I apologize as it looks a bit quick'n'dirty. 
            I am sharing it because if it was useful to me, it might be useful to others. However, it comes with no guarantee of any kind.

Default fiat currency notice: the default fiat currency is EUR. Please adjust the variable 'FIAT_BASE_CURRENCY' below to use it with another base currency. 
                              This is very important for Binance Card export files as this corresponds to the card's currency. This is expected to be minor for export files from other CEXs.

Licence: EUPL 1.2 https://joinup.ec.europa.eu/sites/default/files/custom-page/attachment/2020-03/EUPL-1.2%20EN.txt
Author: Vincent Poulain, 2022-2024
'''

from __future__ import annotations

import csv
import logging
import os
import sys

from typing import TextIO


FIAT_BASE_CURRENCY = 'EUR'

CSV_DELIMITER_OUT = ';'
CSV_DELIMITER_IN_BINANCECARD = ';'

MODE_MERIA = 'meria'
MODE_ETHERLINK = 'etherlink'

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class OutputLine:
    def __init__(
            self, 
            txDate: str, 
            sentAmount: str, sentCurrency: str, 
            receivedAmount: str, receivedCurrency: str, *, 
            feeAmount: str = None, feeCurrency: str = None, 
            netWorthAmount: str = None, netWorthCurrency: str = None, 
            label: str = None, description: str = None, txHash: str = None
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


    def toList(self) -> list[str]:
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
    

    def __repr__(self) -> str:
        return repr(self.toList())
    

    @staticmethod
    def headers() -> OutputLine:
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


def usage() -> None:
    logger.error(f'Usage: {sys.argv[0]} {MODE_MERIA}|{MODE_ETHERLINK} path/to/transaction_file.csv [path/to/etherlink_tokens_transfer_file.csv]')


def doConvert() -> None:
    if len(sys.argv) in (3, 4):
        mode = sys.argv[1]

        if (len(sys.argv) == 4 and mode == MODE_MERIA) or (len(sys.argv) == 3 and mode == MODE_ETHERLINK):
            return usage()
    else:
        return usage()
    
    filePathA = sys.argv[2]
    filePathB = None if mode != MODE_ETHERLINK else sys.argv[3]

    lines = None

    try:
        with open(filePathA, newline = '') as inputFileA:
            if mode == MODE_MERIA:
                lines = convertMeria(inputFileA)

            elif mode == MODE_ETHERLINK:
                with open(filePathB, newline = '') as inputFileB:
                    lines = consolidateEtherlink(sorted(convertEtherlinkXtz(inputFileA) + convertEtherlinkTokens(inputFileB), key = lambda x: x.txDate))            

            else:
                logger.error(f'Unknown mode: {mode}. Try "{sys.argv[0]} help" for help.')

        splittedPath = os.path.split(filePathA)

        with open(os.path.join(splittedPath[0], f'koinly_{splittedPath[1]}'), mode = 'w', newline = '') as outputFile:
            writer = csv.writer(outputFile, delimiter = CSV_DELIMITER_OUT, quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(OutputLine.headers().toList())

            for row in lines:
                writer.writerow(row.toList())

    except FileNotFoundError as err:
        logger.error(f'Cannot open "{err.filename}": file not found.')


def csvReader(inputFile: str, delimiter: str) -> csv.reader:
    reader = csv.reader(inputFile, delimiter = delimiter)
    next(reader)

    return reader


def toUnits(amount: str, decimals: str) -> str:
    intDecimals = int(decimals)
    floatResult = int(amount) / int(f'1{intDecimals * "0"}')

    strResult = f'{floatResult:.{intDecimals}f}'

    while (strResult[-1] == '0'):
        strResult = strResult[:-1]
  
    if strResult[-1] == '.':
        strResult = strResult[:-1]
        
    return strResult


def receivedFairAmpunt(receivedAmount: str, sentAmount: str):
    return float(receivedAmount) >= float(sentAmount)
    

def convertMeria(inputFile: TextIO) -> list[OutputLine]:
    def unhandledTxInfoForTxTypeError(txType: str, txInfo: str):
        logger.error(f'Unhandled txInfo for txType {txType}: {txInfo}.')

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
            if txInfo in ('airdrop', 'deposit', 'order', 'reward', 'unstaking', 'resale'):
                receivedAmount = destinationAmount
                receivedCurrency = destinationCurrency

                if feeMultiplier > 0:
                    feeAmount = str(feeMultiplier * float(receivedAmount))
                    feeCurrency = receivedCurrency

                label = (
                    txInfo if txInfo in ('airdrop', 'reward') else 
                        'unstake' if txInfo in ('unstaking', 'resale') else 
                            'liquidity in' if receivedCurrency == FIAT_BASE_CURRENCY else 
                                None
                )

            elif txInfo in ('claim'):
                pass

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
            if sourceCurrency == destinationCurrency:
                continue
            
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
            logger.error(f'Unhandled txType: {txType}.')

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


def convertEtherlinkXtz(inputFile: TextIO) -> list[OutputLine]:
    reader = csvReader(inputFile, ',')
    lines = []

    def toXtz(amount: str) -> str:
        return toUnits(amount, 18)

    for row in reader:
        txHash = row[0]
        txDate = row[2]
        fromAddress = row[3]
        toAddress = row[4]        
        txType = row[6]
        amount = row[7]
        fees = row[8]
        methodName = row[14]
        currency = 'XTZ'

        sentAmount = None
        sentCurrency = None
        receivedAmount = None
        receivedCurrency = None
        feeAmount = None
        feeCurrency = None
        label = None
        description = None        

        if txType == 'IN':
            receivedAmount = toXtz(amount)
            receivedCurrency = currency
            label = methodName if methodName == 'deposit' else None

        elif txType == 'OUT':
            sentAmount = toXtz(amount)
            sentCurrency = currency
            feeAmount = toXtz(fees)
            feeCurrency = currency           
            label = None

        else:
            logger.error(f'Unhandled txType: {txType}.')

        description = f'{txType}{(" (" + methodName + ")") if len(methodName) > 0 else ""}: {fromAddress} to {toAddress}' 

        lines.append(
            OutputLine(
                txDate = txDate,
                sentAmount = sentAmount, sentCurrency = sentCurrency,
                receivedAmount = receivedAmount, receivedCurrency = receivedCurrency,
                feeAmount = feeAmount, feeCurrency = feeCurrency,
                label = label,
                description = description,
                txHash = txHash
            )
        )

    return lines


def convertEtherlinkTokens(inputFile: TextIO) -> list[OutputLine]:
    reader = csvReader(inputFile, ',')
    lines = []
    
    for row in reader:
        txHash = row[0]
        txDate = row[2]
        fromAddress = row[3]
        toAddress = row[4]      
        contractAddress = row[5]  
        txType = row[6]
        tokenDecimals = row[7]
        tokenSymbol = row[8]
        amount = row[9]

        sentAmount = None
        sentCurrency = None
        receivedAmount = None
        receivedCurrency = None
        feeAmount = None
        feeCurrency = None
        label = None
        description = None        

        if len(tokenDecimals) == 0:
            tokenDecimals = 0

        if txType == 'IN':
            receivedAmount = toUnits(amount, tokenDecimals)
            receivedCurrency = tokenSymbol
            label = None

        elif txType == 'OUT':
            sentAmount = toUnits(amount, tokenDecimals)
            sentCurrency = tokenSymbol

            if sentCurrency[:3]  == 'slW' and  toAddress == '0x65fe928c5D04a2DA42347bA9D4d1C3f4952851F5' and contractAddress == '0x008ae222661B6A42e3A097bd7AAC15412829106b':
                receivedAmount = sentAmount
                receivedCurrency = sentCurrency[3:]
                label = 'swap'
                description = f'Unwrapped {sentAmount} {sentCurrency} to {receivedAmount} {receivedCurrency}'

            else:           
                label = None

        else:
            logger.error(f'Unhandled txType: {txType}.')

        if label is None:
            description = f'{txType}: {fromAddress} to {toAddress}' 

        lines.append(
            OutputLine(
                txDate = txDate,
                sentAmount = sentAmount, sentCurrency = sentCurrency,
                receivedAmount = receivedAmount, receivedCurrency = receivedCurrency,
                feeAmount = feeAmount, feeCurrency = feeCurrency,
                label = label,
                description = description,
                txHash = txHash
            )
        )

    return lines


def consolidateEtherlink(txList: list[OutputLine]) -> list[OutputLine]:
    def getTxByIndex(txList: list[OutputLine], index: int) -> OutputLine:
        try:
            return txList[index]
        
        except IndexError:
            return OutputLine(None, None, None, None, None)
        

    consolidatedTxs = []
    skipNext = 0

    for idx in range(len(txList)):
        tx = txList[idx]

        if skipNext > 0:
            skipNext -= 1

        elif tx.description.startswith('OUT (depositETH):'):
            txBack = getTxByIndex(txList, idx + 1)

            if (
                txBack.txDate != tx.txDate or 
                txBack.sentAmount is not None or 
                txBack.sentCurrency is not None or 
                not receivedFairAmpunt(txBack.receivedAmount, tx.sentAmount) or 
                txBack.receivedCurrency != f'slW{tx.sentCurrency}' or
                txBack.txHash != tx.txHash
            ):
                logger.error(f'No consistent back transaction for OUT depositETH: {tx.txDate}')
                consolidatedTxs.append(tx)

            else:
                consolidatedTxs.append(OutputLine(
                        txDate = tx.txDate, 
                        sentAmount = tx.sentAmount, sentCurrency = tx.sentCurrency, 
                        receivedAmount = txBack.receivedAmount, receivedCurrency = txBack.receivedCurrency,
                        feeAmount = tx.feeAmount, feeCurrency = tx.feeCurrency, 
                        label = 'swap', description = f'Deposited {tx.sentAmount} {tx.sentCurrency}',
                        txHash = tx.txHash
                    )
                )

                skipNext = 1

        elif tx.description.startswith('OUT (supply):'):
            txBackA = getTxByIndex(txList, idx + 1)
            txBackB = getTxByIndex(txList, idx + 2)

            if (
                txBackA.txDate != tx.txDate or txBackB.txDate != tx.txDate or
                txBackA.sentAmount is None or 
                txBackA.sentCurrency is None or 
                not receivedFairAmpunt(txBackB.receivedAmount, txBackA.sentAmount) or 
                txBackB.receivedCurrency != f'sl{txBackA.sentCurrency}' or
                txBackA.txHash != tx.txHash or txBackB.txHash != tx.txHash
            ):
                logger.error(f'No consistent back transactions for supply: {tx.txDate}')
                consolidatedTxs.append(tx)

            else:
                tx.description = f'Unlocked {txBackA.sentCurrency} for OUT supply'
                consolidatedTxs.append(tx)

                consolidatedTxs.append(OutputLine(
                        txDate = tx.txDate, 
                        sentAmount = txBackA.sentAmount, sentCurrency = txBackA.sentCurrency, 
                        receivedAmount = txBackB.receivedAmount, receivedCurrency = txBackB.receivedCurrency,
                        feeAmount = txBackA.feeAmount, feeCurrency = tx.feeCurrency, 
                        label = 'swap', description = f'Supplied {txBackA.sentAmount} {txBackA.sentCurrency}',
                        txHash = tx.txHash
                    )
                )

                skipNext = 2

        elif tx.description.startswith('OUT (withdrawETH):'):
            txBack = getTxByIndex(txList, idx + 1)

            if (
                txBack.txDate != tx.txDate or 
                txBack.sentAmount is not None or 
                txBack.sentCurrency is not None or 
                txBack.receivedAmount is None or 
                txBack.receivedCurrency != f'slW{tx.sentCurrency}' or
                txBack.txHash != tx.txHash
            ):
                logger.error(f'No consistent back transaction for OUT withdrawETH: {tx.txDate}')
                consolidatedTxs.append(tx)

            else:
                consolidatedTxs.append(OutputLine(
                        txDate = tx.txDate, 
                        sentAmount = tx.sentAmount, sentCurrency = tx.sentCurrency, 
                        receivedAmount = txBack.receivedAmount, receivedCurrency = txBack.receivedCurrency,
                        feeAmount = tx.feeAmount, feeCurrency = tx.feeCurrency, 
                        label = None, description = f'Unlocked {tx.sentCurrency} for redeem',
                        txHash = tx.txHash
                    )
                )

                skipNext = 1

        elif tx.description.startswith('OUT (withdraw):'):
            txBackA = getTxByIndex(txList, idx + 1)
            txBackB = getTxByIndex(txList, idx + 2)

            if (
                txBackA.txDate != tx.txDate or txBackB.txDate != tx.txDate or
                txBackA.sentAmount is None or 
                txBackA.sentCurrency != f'sl{txBackB.receivedCurrency}' or 
                not receivedFairAmpunt(txBackB.receivedAmount, txBackA.sentAmount) or 
                txBackB.receivedCurrency is None or
                txBackA.txHash != tx.txHash or txBackB.txHash != tx.txHash
            ):
                logger.error(f'No consistent back transactions for withdraw: {tx.txDate}')
                consolidatedTxs.append(tx)

            else:
                tx.description = f'Unlocked {txBackA.sentCurrency} for OUT withdraw'
                consolidatedTxs.append(tx)

                consolidatedTxs.append(OutputLine(
                        txDate = tx.txDate, 
                        sentAmount = txBackA.sentAmount, sentCurrency = txBackA.sentCurrency, 
                        receivedAmount = txBackB.receivedAmount, receivedCurrency = txBackB.receivedCurrency,
                        feeAmount = txBackA.feeAmount, feeCurrency = tx.feeCurrency, 
                        label = 'swap', description = f'Redeemed {txBackA.sentAmount} {txBackA.sentCurrency}',
                        txHash = tx.txHash
                    )
                )

                skipNext = 2
                
        elif tx.description.startswith('OUT (multicall):'):
            txBack = getTxByIndex(txList, idx + 1)

            if (
                txBack.txDate != tx.txDate or 
                txBack.sentAmount is not None or 
                txBack.sentCurrency is not None or 
                txBack.receivedAmount is None or 
                txBack.receivedCurrency == tx.receivedCurrency or
                txBack.txHash != tx.txHash
            ):
                logger.error(f'No consistent back transaction for OUT multicall: {tx.txDate}')
                consolidatedTxs.append(tx)

            else:
                consolidatedTxs.append(OutputLine(
                        txDate = tx.txDate, 
                        sentAmount = tx.sentAmount, sentCurrency = tx.sentCurrency, 
                        receivedAmount = txBack.receivedAmount, receivedCurrency = txBack.receivedCurrency,
                        feeAmount = tx.feeAmount, feeCurrency = tx.feeCurrency, 
                        label = 'swap', description = f'Swapped {tx.sentAmount} {tx.sentCurrency} to {txBack.receivedAmount} {txBack.receivedCurrency}',
                        txHash = tx.txHash
                    )
                )

                skipNext = 1

        elif tx.description.startswith('OUT (bridge):'):
            txBack = getTxByIndex(txList, idx + 1)

            if (
                txBack.txDate != tx.txDate or
                tx.sentAmount is None or
                tx.sentCurrency != 'XTZ' or
                txBack.sentAmount is None or
                txBack.sentCurrency is None or
                txBack.txHash != tx.txHash
            ):
                logger.error(f'No consistent back transaction for OUT bridge: {tx.txDate}')
                consolidatedTxs.append(tx)

            else:
                consolidatedTxs.append(OutputLine(
                        txDate = tx.txDate, 
                        sentAmount = None, sentCurrency = None,
                        receivedAmount = None, receivedCurrency = None,
                        feeAmount = tx.sentAmount, feeCurrency = tx.sentCurrency, 
                        label = None, description = f'Bridge foreign gas fees',
                        txHash = tx.txHash
                    )
                )

                consolidatedTxs.append(OutputLine(
                        txDate = tx.txDate, 
                        sentAmount = txBack.sentAmount, sentCurrency = txBack.sentCurrency,
                        receivedAmount = None, receivedCurrency = None,
                        label = None, description = f'Bridged out {txBack.sentAmount} {txBack.sentCurrency}',
                        txHash = tx.txHash
                    )
                )

                skipNext = 1

        else:
            consolidatedTxs.append(tx)

    return consolidatedTxs


if __name__ == '__main__':
    doConvert()

