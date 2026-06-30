"""AIPA package for IB Wallet.

Provides dispatch contract models, validation, and routing helpers.
"""

from .contracts import AIPAResponse, AIPADispatch, WalletAction
from .gate import FastGateError, validate_dispatch
from .router import dispatch_to_wallet
