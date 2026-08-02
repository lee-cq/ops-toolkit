#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : main
@Author     : LeeCQ
@Date-Time  : 2026/8/1 


"""
import logging
import sys
import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / 'deps'))

from base import Test0800, Test0815

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


def main():
    """"""
    Test0800(today=datetime.date(2026, 7, 30)).main()
    Test0815(today=datetime.date(2026, 7, 30)).main()



if __name__ == '__main__':
    main()