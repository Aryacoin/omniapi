import urlparse
import os, sys, re, random,pybitcointools, bitcoinrpc, math, hashlib
from decimal import Decimal
from flask import Flask, request, jsonify, abort, json, make_response
from rpcclient import *

sys.path.append("/usr/local/lib/armory/")
from armoryengine.ALL import *

app = Flask(__name__)
app.debug = True

@app.route('/getunsigned', methods=['POST'])
def generate_unsigned():
    unsigned_hex = request.form['unsigned_hex']
    pubkey = request.form['pubkey']
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(hashlib.sha256(hex_to_binary(pubkey)).digest())
    pubKeyHash = binary_to_hex(ripemd160.digest())
    try:
        tnet_ = request.form['testnet']
    except KeyError, e:
        tnet_ = 0
    #Translate raw txn
    decoded_tx = decoderawtransaction(unsigned_hex)['result']
    tnet = 'fabfb5da' if tnet_ else 'f9beb4d9'

    keys = [{ 'dersighex': '', 'pubkeyhex': pubkey, 'wltlochex': '' }]

    i_k = []
    for intx in decoded_tx['vin']:
      spending_txid= intx['txid']
      spending_tx_raw = getrawtransaction(spending_txid)['result']['hex']
      spending_tx_decoded = decoderawtransaction(spending_tx_raw)['result']
      i_vout = -1
      for each in spending_tx_decoded['vout']:
        info=each['scriptPubKey']['asm'].split(' ')
        print "\nArmoryService: Searching for pubKey:", pubKeyHash, "| ASM Info:",info
        if len(info) > 3 and info[0] != "OP_RETURN" and info[2] == pubKeyHash:
          i_vout = each['n']

      i_k.append ({'contribid': '',
                      'contriblabel': '',
                      'keys': keys,
                      'magicbytes': tnet,
                      'numkeys': 1,
                      'p2shscript': '',
                      'sequence': 4294967295,
                      'supporttx': spending_tx_raw,
                      'supporttxoutindex': i_vout,
                      'version': 1})

    o_k = []
    for o in decoded_tx['vout']:
      o_k.append( {    'authdata': '',
                       'authmethod': 'NONE',
                       'contribid': '',
                       'contriblabel': '',
                       'magicbytes': tnet,
                       'p2shscript': '',
                       'txoutscript': o['scriptPubKey']['hex'],
                       'txoutvalue': int( Decimal(o['value']) * Decimal(1e8) ),
                       'version': 1,
                       'wltlocator': ''})

    json_nosig = {
    'id': '',
    'locktimeint': 0,
    'magicbytes': tnet,
    'version': 1,
    'inputs': i_k,
    'outputs': o_k
    }

    unsigned_tx_ascii= UnsignedTransaction().fromJSONMap(json_nosig, True).serializeAscii()

    print("\n\nArmoryService: Output is:\n%s" % unsigned_tx_ascii)
    return jsonify({'armoryUnsigned':unsigned_tx_ascii})

@app.route('/getrawtransaction', methods=['POST'])
def get_raw():
  """Converts a signed tx from armory's offline format to a raw hex tx that bitcoind can broadcast/use"""

  signed_tx_ascii = request.form['signed_hex']
  print("\nArmoryService: REQUEST(convert_signed_tx_to_raw_hex) -- signed_tx_ascii:\n'%s'\n" % (signed_tx_ascii,))

  try:
      utx = UnsignedTransaction()
      utx.unserializeAscii(signed_tx_ascii)
  except Exception, e:
      raise Exception("Could not decode transaction: %s" % e)

  try:
    if not utx.evaluateSigningStatus().canBroadcast:
      pytx = utx.getUnsignedPyTx()
      signed=False
    else:
      pytx = utx.getSignedPyTx()
      signed=True
    raw_tx_bin = pytx.serialize()
    raw_tx_hex = binary_to_hex(raw_tx_bin)
  except Exception, e:
    raise Exception("Could not serialize transaction: %s" % e)

  return jsonify({'signed':signed, 'rawTransaction':raw_tx_hex})
