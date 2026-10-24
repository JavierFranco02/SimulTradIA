"""Adaptadores a servicios EXTERNOS (yfinance, ccxt, Finnhub, modelo de lenguaje...).

Solo traen datos de afuera y los devuelven como entidades o estructuras simples.
No escriben en la BD (eso es del repositorio) ni deciden nada (eso es del servicio).
Así los servicios se prueban con un cliente falso, sin red.
"""
