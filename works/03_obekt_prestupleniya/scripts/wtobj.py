# -*- coding: utf-8 -*-
import wtobj_p1, wtobj_p2, wtobj_p3, wtobj_p4, wtobj_src
TITLE = wtobj_p1.TITLE
BLOCKS = (wtobj_p1.BLOCKS + wtobj_p2.BLOCKS + wtobj_p3.BLOCKS + wtobj_p4.BLOCKS
          + [('h1','СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ')] + wtobj_p4.NPA
          + [('h2','Учебная, научная литература')] + [('item', s) for s in wtobj_src.LIT]
          + wtobj_p4.EMP)
