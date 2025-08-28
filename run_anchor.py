#!/usr/bin/env python3
"""
Teo Personal Assistant Bot - Anchor UX Entry Point
Run this file to start your bot with Anchor UX
"""
import sys
import logging
import os

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.anchor_main import main

if __name__ == '__main__':
    main()
