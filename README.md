# Crypto Bot

This project is a backend service for a crypto trading bot, developed to interact with the Polygon blockchain. It is implemented using Python with the Flask framework and leverages the Web3.py library for blockchain interactions. The bot is capable of executing various actions such as buying, selling, and swapping tokens, as well as performing automated rebalances based on insights. It also provides endpoints to retrieve token prices and transaction logs.

**This bot is designed for educational and study purposes only. It is not intended for use in actual trading activities.**

[![Python 3.9](https://img.shields.io/badge/Python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![Flask](https://img.shields.io/badge/Flask-2.0.1-green.svg)](https://flask.palletsprojects.com/en/2.0.x/)
[![Web3.py](https://img.shields.io/badge/Web3.py-5.24.0-orange.svg)](https://web3py.readthedocs.io/en/stable/)

## License

This software is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.

## Author

This software was written by [Gustavo Polli](https://github.com/matthewwithanm).

## Contributing

Contributions are welcome! Please open a pull request or issue on the [GitHub repository](https://github.com/gapolli/crypto-bot).

## Endpoints

### `POST /send`

Sends the given amount of crypto to the specified address.

#### Request Body

* `recipientAddress`: string - The recipient's wallet address
* `amountInPol`: number - The amount of crypto to send in POL

#### Response

* `transactionHash`: string - The transaction hash

### `POST /buy`

Buys the given amount of crypto in USD.

#### Request Body

* `amountInUsd`: number - The amount of crypto to buy in USD

#### Response

* `transactionHash`: string - The transaction hash

### `POST /sell`

Sells the given amount of crypto in POL.

#### Request Body

* `amountInPol`: number - The amount of crypto to sell in POL

#### Response

* `transactionHash`: string - The transaction hash

### `POST /swap`

Swaps the given amount of tokens.

#### Request Body

* `tokenIn`: string - The token to swap in
* `tokenOut`: string - The token to swap out
* `amountIn`: number - The amount of tokens to swap in

#### Response

* `transactionHash`: string - The transaction hash

### `POST /analyze`

Performs a fundamentalist analysis on the given token.

#### Request Body

* `tokenAddress`: string - The address of the token to analyze
* `days`: number - The number of days to analyze
* `interval`: string - The interval to analyze (e.g. "1 hour", "1 day", "1 week")

#### Response

* `trend`: string - The trend of the token (e.g. "up", "down", "neutral")
* `score`: number - A score indicating the strength of the trend (0-100)

