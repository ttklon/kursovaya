# -*- coding: utf-8 -*-
import w240_p1, w240_p2, w240_p3, w240_p4, w240_src
TITLE = w240_p1.TITLE
BLOCKS = (w240_p1.BLOCKS + w240_p2.BLOCKS + w240_p3.BLOCKS + w240_p4.BLOCKS
          + [('h1','СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ')] + w240_p4.NPA
          + [('h2','Учебная, научная литература')] + [('item', s) for s in w240_src.LIT]
          + w240_p4.EMP)
