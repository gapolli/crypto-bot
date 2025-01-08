"""
Flask API for interacting with the Polygon blockchain.

The API provides endpoints for sending transactions, buying and selling POL
tokens, and swapping tokens using Uniswap.

The API uses the Web3.py library for interacting with the Polygon blockchain.

The API endpoints are as follows:

- `/send`: POST endpoint for sending a transaction to a recipient address.
- `/buy-pol`: POST endpoint for buying POL tokens with USD.
- `/sell-pol`: POST endpoint for selling POL tokens for USD.
- `/swap-pol`: POST endpoint for swapping POL tokens for another token.
- `/auto-rebalance`: POST endpoint for performing an automated rebalance
  of tokens based on insights.

The API requires a configuration file (`config.json`) with the following
parameters:

- `server`: object with `host` and `port` parameters for the Flask server.
- `network`: object with `polygon_rpc_url` parameter for the Polygon RPC
  endpoint.
- `wallet`: object with `address` and `private_key` parameters for the
  wallet to use.
- `contracts`: object with `pol_address`, `dai_address`, and `router_address`
  parameters for the POL, DAI, and UniswapV2Router contract addresses.
- `uniswap`: object with `router_abi_path` parameter for the path to the
  UniswapV2Router ABI file.
- `logging`: object with `level` and `file` parameters for the logging level
  and log file path.
"""
import json
import logging
import os
import time
from web3 import Web3
from web3.middleware import geth_poa_middleware

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Set up config
with open('config.json') as f:
    config = json.load(f)

# Set up logging to a file
log_file = config['logging']['file']
logger.addHandler(logging.FileHandler(log_file))

# Set up Web3 provider
polygon_rpc_url = config['network']['polygon_rpc_url']
w3 = Web3(Web3.HTTPProvider(polygon_rpc_url))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Set up wallet
private_key = config['wallet']['private_key']
wallet_address = w3.eth.account.from_key(private_key).address

# Set up token addresses
pol_address = config['contracts']['pol_address']

# Set up Flask app
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/send', methods=['POST'])
def send_transaction():
    """
    Send a transaction to a recipient address.

    This endpoint takes a JSON payload with the following parameters:

    - `recipient_address`: string - The recipient's wallet address
    - `amount_in_pol`: number - The amount of POL to send in POL

    It will send the transaction to the recipient, and log the action to the
    log file.

    Returns:
        JSON response with the following data:
        - `transaction_hash`: string - The transaction hash
    """
    data = request.get_json()
    recipient_address = data.get('recipient_address')
    amount_in_pol = data.get('amount_in_pol')

    if recipient_address is None or amount_in_pol is None:
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        # Prepare transaction details
        tx = {
            'to': recipient_address,
            'value': w3.utils.to_wei(str(amount_in_pol), 'ether')
        }

        # Send the transaction
        tx_hash = w3.eth.send_transaction(tx)
        w3.eth.wait_for_transaction_receipt(tx_hash)

        # Log the action
        logger.info(f'Sent {amount_in_pol} POL to {recipient_address}')

        # Write quantitative data to log file
        with open(config['logging']['file'], 'a') as f:
            f.write(f'{time.time()},{amount_in_pol},{recipient_address}\n')

        # Send success response with transaction hash
        return jsonify({'transaction_hash': tx_hash.hex()}), 200
    except Exception as e:
        # Log the error
        logger.error(f'Error sending transaction: {e}')

        # Send failure response with error message
        return jsonify({'error': str(e)}), 500

@app.route('/buy-pol', methods=['POST'])
def buy_pol():
    """Buy POL tokens with USD."""
    data = request.get_json()
    amount_in_usd = data.get('amount_in_usd')

    if amount_in_usd is None:
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        # Get current POL price in USD
        pol_price = get_pol_price()
        amount_in_pol = amount_in_usd / pol_price

        # Get DAI token address
        dai_address = config['contracts']['dai_address']

        # Get AMM router contract
        with open(config['uniswap']['router_abi_path']) as f:
            router_abi = json.load(f)
        router_contract = w3.eth.contract(
            address=config['contracts']['router_address'],
            abi=router_abi
        )

        # Prepare path for swap
        path = [dai_address, pol_address]

        # Get amount of POL tokens to receive
        amount_out = router_contract.functions.getAmountsOut(
            w3.toWei(str(amount_in_usd), 'ether'),
            path
        ).call()[-1]

        # Prepare transaction details
        tx = router_contract.functions.swapExactTokens(
            w3.toWei(str(amount_in_usd), 'ether'),
            amount_out,
            path,
            wallet_address,
            int(time.time()) + 100
        ).buildTransaction({
            'from': wallet_address,
            'nonce': w3.eth.get_transaction_count(wallet_address)
        })

        # Sign and send the transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)

        # Log the action
        logger.info(f'Bought {amount_in_pol} POL with {amount_in_usd} USD')

        # Write quantitative data to log file
        with open(log_file, 'a') as f:
            f.write(f'{time.time()},{amount_in_pol},{amount_in_usd}\n')

        # Send success response with transaction hash
        return jsonify({'transaction_hash': tx_hash.hex()}), 200
    except Exception as e:
        # Log the error
        logger.error(f'Error buying POL: {e}')

        # Send failure response with error message
        return jsonify({'error': str(e)}), 500

@app.route('/get-pol-price', methods=['GET'])
def get_pol_price():
    """
    Get the current POL price in USD using a price oracle.

    Returns:
        JSON response with the following data:
        - `price`: float - The current price of POL in USD
    """
    try:
        # Get current POL price from oracle
        price_feed = w3.eth.contract(
            address=config['contracts']['price_feed_address'],
            abi=[{
                'constant': True,
                'inputs': [],
                'name': 'latestAnswer',
                'outputs': [{'name': '', 'type': 'int256'}],
                'payable': False,
                'stateMutability': 'view',
                'type': 'function'
            }]
        )
        price = price_feed.functions.latestAnswer().call() / 10**8

        # Write quantitative data to log file
        with open(log_file, 'a') as f:
            f.write(f'{time.time()},{price}\n')

        # Return success response with price
        return jsonify({'price': price}), 200
    except Exception as e:
        # Log the error
        logger.error(f'Error getting POL price: {e}')

        # Send failure response with error message
        return jsonify({'error': str(e)}), 500

@app.route('/rebalance', methods=['POST'])
def rebalance():
    """
    Rebalance the given token pair.

    This function handles POST requests to the `/rebalance` endpoint.
    It reads token pair and amount details from the request body, validates them,
    and performs a liquidity add operation using UniswapV2Router.

    Returns:
        JSON response with transaction hash on success, or an error message on failure.
    """
    data = request.get_json()
    token_a = data.get('token_a')
    token_b = data.get('token_b')
    amount_a = data.get('amount_a')
    amount_b = data.get('amount_b')

    if not all([token_a, token_b, amount_a, amount_b]):
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        # Get current balances of the tokens
        token_a_balance = w3.eth.get_balance(token_a)
        token_b_balance = w3.eth.get_balance(token_b)

        # Calculate the amount of tokenA to sell and tokenB to buy
        amount_a_to_sell = int(amount_a * token_a_balance / 10**18)
        amount_b_to_buy = int(amount_b * token_b_balance / 10**18)

        # Load Uniswap router contract
        router = w3.eth.contract(
            address=config['contracts']['router_address'],
            abi=json.load(open(config['uniswap']['router_abi_path']))
        )

        # Add liquidity to the pool
        tx = router.functions.addLiquidity(
            token_a,
            token_b,
            amount_a_to_sell,
            amount_b_to_buy,
            1,
            1,
            wallet_address,
            int(time.time()) + 60
        ).transact({'from': wallet_address})

        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx)

        # Log the action
        logger.info(f'Rebalanced tokens: {amount_a_to_sell} of {token_a}, {amount_b_to_buy} of {token_b}')

        # Write quantitative data to log file
        with open(log_file, 'a') as f:
            f.write(f'{time.time()},{amount_a_to_sell},{amount_b_to_buy}\n')

        # Return success response with transaction hash
        return jsonify({'transaction_hash': tx_receipt.transactionHash.hex()}), 200
    except Exception as e:
        # Log the error
        logger.error(f'Error rebalancing tokens: {e}')

        # Send failure response with error message
        return jsonify({'error': str(e)}), 500

@app.route('/rebalance-insights', methods=['GET'])
def get_rebalance_insights():
    """
    Get insights on when to rebalance tokens using machine learning.

    Returns:
        JSON response with the following data:
        - `buy`: boolean - Whether it is a good time to buy tokens
        - `sell`: boolean - Whether it is a good time to sell tokens
        - `rebalance`: boolean - Whether it is a good time to rebalance tokens

    Description:
        This endpoint uses a simple moving average model to predict when to rebalance tokens.
        The model takes into account the last 10 data points from the log file and calculates the
        average of the token amounts. If the current token amount is greater than 10% above the
        average, it is a good time to buy tokens. If the current token amount is less than 10%
        below the average, it is a good time to sell or rebalance tokens.
    """
    # Load data from log file
    data = []
    log_file_path = config['logging']['file']
    with open(log_file_path, 'r') as f:
        for line in f:
            timestamp, amount_a, amount_b = line.strip().split(',')
            data.append((int(timestamp), float(amount_a), float(amount_b)))

    # Train a machine learning model to predict when to rebalance tokens
    # For now, use a simple moving average model
    window_size = 10
    buy = False
    sell = False
    rebalance = False
    if len(data) >= window_size:
        avg_a = sum(x[1] for x in data[-window_size:]) / window_size
        avg_b = sum(x[2] for x in data[-window_size:]) / window_size
        if data[-1][1] > avg_a * 1.1:
            buy = True
        elif data[-1][2] > avg_b * 1.1:
            sell = True
        elif data[-1][1] < avg_a * 0.9 or data[-1][2] < avg_b * 0.9:
            rebalance = True

    # Return insights
    return jsonify({
        'buy': buy,
        'sell': sell,
        'rebalance': rebalance
    }), 200

@app.route('/auto-rebalance', methods=['POST'])
def auto_rebalance():
    """
    Perform an automated rebalance of tokens based on the insights.

    Returns:
        JSON response with the following data:
        - `transaction_hash`: string - The transaction hash of the rebalance
    """
    # Get insights on whether to rebalance
    insights_response = get_rebalance_insights()
    insights = insights_response.json()
    
    # Check if rebalancing is recommended
    if insights.get('rebalance'):
        # Extract token and amount details from request
        data = request.get_json()
        token_a = data.get('token_a')
        token_b = data.get('token_b')
        amount_a = data.get('amount_a')
        amount_b = data.get('amount_b')

        # Validate required parameters
        if not all([token_a, token_b, amount_a, amount_b]):
            return jsonify({'error': 'Missing required parameters'}), 400

        try:
            # Get the current balances of the tokens
            token_a_balance = w3.eth.get_balance(token_a)
            token_b_balance = w3.eth.get_balance(token_b)

            # Calculate the amount of tokenA to sell and tokenB to buy
            amount_a_to_sell = int(amount_a * token_a_balance / 10**18)
            amount_b_to_buy = int(amount_b * token_b_balance / 10**18)

            # Load Uniswap router contract
            router_abi = json.load(open(config['uniswap']['router_abi_path']))
            router_address = config['contracts']['router_address']
            router_contract = w3.eth.contract(address=router_address, abi=router_abi)

            # Prepare path for swap and calculate output tokens
            path = [token_a, token_b]
            amount_out = router_contract.functions.getAmountsOut(
                w3.utils.to_wei(str(amount_a_to_sell), 'ether'),
                path
            ).call()[-1]

            # Build transaction
            tx = router_contract.functions.swapExactTokens(
                w3.utils.to_wei(str(amount_a_to_sell), 'ether'),
                amount_out,
                path,
                wallet_address,
                int(time.time()) + 100
            ).buildTransaction({
                'from': wallet_address,
                'nonce': w3.eth.get_transaction_count(wallet_address)
            })

            # Send the transaction and wait for receipt
            tx_hash = w3.eth.send_transaction(tx)
            w3.eth.wait_for_transaction_receipt(tx_hash)

            # Log the successful rebalance action
            logger.info(f'Auto-rebalanced {amount_a_to_sell} {token_a} for {amount_b_to_buy} {token_b}')

            # Return success response with transaction hash
            return jsonify({'transaction_hash': tx_hash.hex()}), 200
        except Exception as e:
            # Log the error
            logger.error(f'Error auto-rebalancing: {e}')

            # Send failure response with error message
            return jsonify({'error': str(e)}), 500

@app.route('/log', methods=['GET'])
def get_log():
    """
    Get the log of all transactions.

    Returns:
        JSON response with the following data:
        - `log`: string - The log of all transactions
    """
    try:
        # Read log file
        with open(log_file, 'r') as f:
            log = f.read()

        # Return success response with log
        return jsonify({'log': log}), 200
    except Exception as e:
        # Log the error
        logger.error(f'Error reading log: {e}')

        # Send failure response with error message
        return jsonify({'error': str(e)}), 500

@app.route('/get-pol-price', methods=['GET'])
def get_pol_price():
    """
    Get the current price of POL in USD.

    Returns:
        JSON response with the following data:
        - `price`: float - The current price of POL in USD
    """
    try:
        # Get current POL price from oracle
        price_feed_abi = json.load(open(config['uniswap']['price_feed_abi_path']))
        price_feed_address = config['contracts']['price_feed_address']
        price_feed_contract = w3.eth.contract(address=price_feed_address, abi=price_feed_abi)
        price = price_feed_contract.functions.latestAnswer().call() / 10**8

        # Return success response with price
        return jsonify({'price': price}), 200
    except Exception as e:
        # Log the error
        logger.error(f'Error getting POL price: {e}')

        # Send failure response with error message
        return jsonify({'error': str(e)}), 500

@app.route('/get-dai-price', methods=['GET'])
def get_dai_price():
    """
    Get the current price of DAI in USD.

    Returns:
        JSON response with the following data:
        - `price`: float - The current price of DAI in USD
    """
    try:
        # Get current DAI price from oracle
        price_feed_abi = json.load(open(config['uniswap']['price_feed_abi_path']))
        price_feed_address = config['contracts']['price_feed_address']
        price_feed_contract = w3.eth.contract(address=price_feed_address, abi=price_feed_abi)
        price = price_feed_contract.functions.latestAnswer().call() / 10**8

        # Return success response with price
        return jsonify({'price': price}), 200
    except Exception as e:
        # Log the error
        logger.error(f'Error getting DAI price: {e}')

        # Send failure response with error message
        return jsonify({'error': str(e)}), 500

# TODO: connect wallet
# TODO: learn user preferences