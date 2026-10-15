"""进程内共享文件锁（v0.17.2）：总线侧与分路侧两个引擎线程把数据写进**同一个** CSV 文件（realtime / events / nilm），
按 source_id 区分。两个 writer 实例各持自己的文件句柄（追加模式 + 每行 flush），这里的锁保证：
① 新文件表头只写一次（open 时检查「文件为空」与写表头在同一临界区）；② 整行写入不交错。"""
from __future__ import annotations

import threading

SHARED_FILE_LOCK = threading.RLock()
