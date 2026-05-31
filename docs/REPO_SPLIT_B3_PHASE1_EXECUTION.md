# B3 Phase-1 Extraction Execution

Tracker: #136
Date: 2026-05-31
Branch: feat/b3-extract-releases-loader
Status: IN_PROGRESS

## Scope

Move Pro-target release loader payloads from Core to ctoa-pro:
- releases/loader/**
- scripts/ops/release-loader.ps1

## Destination Confirmation

- ctoa-pro repo: https://github.com/famatyyk/ctoa-pro
- import commit: 8b01a64
- destination path: releases/loader/**

## Core Policy Alignment

Kept in Core:
- releases/evidence/** (governance and sprint sign-off evidence)
- release notes and docs under releases/* excluding loader payloads

## Notes

B3 extraction keeps Core governance evidence intact while moving commercial loader payloads to Pro repo.
