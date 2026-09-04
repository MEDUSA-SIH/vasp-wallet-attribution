# data/synthetic

Offline demo dataset (Phase 21/22). Stage 0 ships an empty directory; the
real synthetic CSV / parquet files arrive in the next stage.

Expected schema (once present):

```
chains.csv
    code,name,native_symbol
    bitcoin,Bitcoin,BTC
    ethereum,Ethereum,ETH
    ...

wallets.csv
    address,chain,label,tags
    1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa,bitcoin,Satoshi Genesis,historic
    ...

transactions.csv
    chain,tx_hash,from_addr,to_addr,amount,asset,timestamp
    ...
```

These files are intentionally git-ignored (see root .gitignore) once they
contain anything other than this README.