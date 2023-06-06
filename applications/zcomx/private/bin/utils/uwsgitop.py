#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
uwsgitop

Script to run a top-like analysis of uwsgi.
"""
import socket
import json
import curses
import time
import atexit
import sys
import traceback
from collections import defaultdict
import errno
# pylint: disable=bare-except
# pylint: disable=invalid-name
# pylint: disable=missing-docstring
# pylint: disable=line-too-long

NEED_RESET = True
SCREEN = None


def human_size(number):
    # G
    if number >= (1024 * 1024 * 1024):
        return "%.1fG" % (number / (1024 * 1024 * 1024))
    # M
    if number >= (1024 * 1024):
        return "%.1fM" % (number / (1024 * 1024))
    # K
    if number >= 1024:
        return "%.1fK" % (number / 1024)
    return "%d" % number


def game_over():
    if NEED_RESET:
        curses.endwin()


def exc_hook(type, value, tb):
    # pylint: disable=redefined-builtin     # type
    # pylint: disable=global-statement
    global NEED_RESET
    NEED_RESET = False
    if SCREEN:
        curses.endwin()
    traceback.print_exception(type, value, tb)


sys.excepthook = exc_hook

argc = len(sys.argv)

if argc < 2:
    raise Exception("You have to specify the uWSGI stats socket")

addr = sys.argv[1]
sfamily = socket.AF_UNIX
addr_tuple = addr
if ':' in addr:
    sfamily = socket.AF_INET
    addr_parts = addr.split(':')
    addr_tuple = (addr_parts[0], int(addr_parts[1]))

freq = 1
try:
    freq = int(sys.argv[2])
except:
    pass

SCREEN = curses.initscr()
curses.start_color()

try:
    # busy
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    # cheap
    curses.init_pair(2, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    # respawn
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    # sig
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    # pause
    curses.init_pair(5, curses.COLOR_BLUE, curses.COLOR_BLACK)
except curses.error:
    # the terminal doesn't support colors
    pass

atexit.register(game_over)

try:
    curses.curs_set(0)
except:
    pass
SCREEN.clear()


def reqcount(item):
    return item['requests']


def calc_percent(tot, req):
    if tot == 0:
        return 0.0
    return (100 * float(req)) / float(tot)


def merge_worker_with_cores(workers, rps_per_worker, cores, rps_per_core):
    workers_by_id = {w['id']:w for w in workers}
    new_workers = []
    for worker_id, w_cores in cores.items():
        for core in w_cores:
            cid = core['id']
            data = dict(workers_by_id.get(worker_id))
            data.update(core)
            if data['status'] == 'busy' and not core['in_request']:
                data['status'] = '-'
            new_wid = "{0}:{1}".format(worker_id, cid)
            data['id'] = new_wid
            rps_per_worker[new_wid] = rps_per_core[worker_id, cid]
            new_workers.append(data)
    workers[:] = new_workers


def run():
    # RPS calculation
    last_tot_time = time.time()
    last_reqnumber_per_worker = defaultdict(int)
    last_reqnumber_per_core = defaultdict(int)

    # 0 - do not show async core
    # 1 - merge core statistics with worker statistics
    # 2 - display active cores under workers
    async_mode = 0
    fast_screen = 0

    while True:
        if fast_screen == 1:
            SCREEN.timeout(100)
        else:
            SCREEN.timeout(freq * 1000)

        SCREEN.clear()

        json_str = ''

        try:
            s = socket.socket(sfamily, socket.SOCK_STREAM)
            s.connect(addr_tuple)

            while True:
                data = s.recv(4096)
                if len(data) < 1:
                    break
                json_str += data.decode('utf8')
        except IOError as err:
            if err.errno != errno.EINTR:
                raise
            continue
        except:
            raise Exception("unable to get uWSGI statistics")

        dd = json.loads(json_str)

        uversion = ''
        if 'version' in dd:
            uversion = '-' + dd['version']

        if 'listen_queue' not in dd:
            dd['listen_queue'] = 0

        cwd = ""
        if 'cwd' in dd:
            cwd = "- cwd: %s" % dd['cwd']

        uid = ""
        if 'uid' in dd:
            uid = "- uid: %d" % dd['uid']

        gid = ""
        if 'gid' in dd:
            gid = "- gid: %d" % dd['gid']

        masterpid = ""
        if 'pid' in dd:
            masterpid = "- masterpid: %d" % dd['pid']

        SCREEN.addstr(1, 0, "node: %s %s %s %s %s" % (socket.gethostname(), cwd, uid, gid, masterpid))

        # pylint: disable=consider-using-generator
        if 'vassals' in dd:
            SCREEN.addstr(0, 0, "uwsgi%s - %s - emperor: %s - tyrant: %d" % (uversion, time.ctime(), dd['emperor'], dd['emperor_tyrant']))
            vassal_spaces = max([len(v['id']) for v in dd['vassals']])
            SCREEN.addstr(2, 0, " VASSAL%s\tPID\t" % (' ' * (vassal_spaces - 6)), curses.A_REVERSE)
            pos = 3
            for vassal in dd['vassals']:
                SCREEN.addstr(pos, 0, " %s\t%d" % (vassal['id'].ljust(vassal_spaces), vassal['pid']))
                pos += 1

        elif 'workers' in dd:
            tot = sum([worker['requests'] for worker in dd['workers']])

            rps_per_worker = {}
            rps_per_core = {}
            cores = defaultdict(list)
            dt = time.time() - last_tot_time
            total_rps = 0
            for worker in dd['workers']:
                wid = worker['id']
                curr_reqnumber = worker['requests']
                last_reqnumber = last_reqnumber_per_worker[wid]
                rps_per_worker[wid] = (curr_reqnumber - last_reqnumber) / dt
                total_rps += rps_per_worker[wid]
                last_reqnumber_per_worker[wid] = curr_reqnumber
                if not async_mode:
                    continue
                for core in worker.get('cores', []):
                    if not core['requests']:
                        # ignore unused cores
                        continue
                    wcid = (wid, core['id'])
                    curr_reqnumber = core['requests']
                    last_reqnumber = last_reqnumber_per_core[wcid]
                    rps_per_core[wcid] = (curr_reqnumber - last_reqnumber) / dt
                    last_reqnumber_per_core[wcid] = curr_reqnumber
                    cores[wid].append(core)
                cores[wid].sort(key=reqcount)

            last_tot_time = time.time()

            if async_mode == 1:
                merge_worker_with_cores(dd['workers'], rps_per_worker,
                                        cores, rps_per_core)

            tx = human_size(sum([worker['tx'] for worker in dd['workers']]))
            SCREEN.addstr(0, 0, "uwsgi%s - %s - req: %d - RPS: %d - lq: %d - tx: %s" % (uversion, time.ctime(), tot, int(round(total_rps)), dd['listen_queue'], tx))
            SCREEN.addstr(2, 0, " WID\t%\tPID\tREQ\tRPS\tEXC\tSIG\tSTATUS\tAVG\tRSS\tVSZ\tTX\tReSpwn\tHC\tRunT\tLastSpwn", curses.A_REVERSE)
            pos = 3

            dd['workers'].sort(key=reqcount, reverse=True)
            for worker in dd['workers']:
                sigs = 0
                wtx = human_size(worker['tx'])

                wrunt = worker['running_time'] / 1000
                if wrunt > 9999999:
                    wrunt = "%sm" % str(wrunt / (1000 * 60))
                else:
                    wrunt = str(wrunt)

                wlastspawn = time.strftime("%H:%M:%S", time.localtime(worker['last_spawn']))

                color = curses.color_pair(0)
                if 'signals' in worker:
                    sigs = worker['signals']
                if worker['status'] == 'busy':
                    color = curses.color_pair(1)
                if worker['status'] == 'cheap':
                    color = curses.color_pair(2)
                if worker['rss'] == 0:
                    color = curses.color_pair(3)
                if worker['status'].startswith('sig'):
                    color = curses.color_pair(4)
                if worker['status'] == 'pause':
                    color = curses.color_pair(5)

                wid = worker['id']

                rps = int(round(rps_per_worker[wid]))

                try:
                    SCREEN.addstr(pos, 0, " %s\t%.1f\t%d\t%d\t%d\t%d\t%d\t%s\t%dms\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
                        wid, calc_percent(tot, worker['requests']), worker['pid'], worker['requests'], rps, worker['exceptions'], sigs, worker['status'],
                        worker['avg_rt'] / 1000, human_size(worker['rss']), human_size(worker['vsz']),
                        wtx, worker['respawn_count'], worker['harakiri_count'], wrunt, wlastspawn
                    ), color)
                except:
                    pass
                pos += 1
                if async_mode != 2:
                    continue
                for core in cores[wid]:
                    color = curses.color_pair(0)
                    if core['in_request']:
                        status = 'busy'
                        color = curses.color_pair(1)
                    else:
                        status = 'idle'

                    cid = core['id']
                    rps = int(round(rps_per_core[wid, cid]))
                    try:
                        SCREEN.addstr(pos, 0, "  :%s\t%.1f\t-\t%d\t%d\t-\t-\t%s\t-\t-\t-\t-\t-" % (
                            cid, calc_percent(tot, core['requests']), core['requests'], rps, status,
                        ), color)
                    except:
                        pass
                    pos += 1

        SCREEN.refresh()

        s.close()
        ch = SCREEN.getch()
        if ch == ord('q'):
            game_over()
            break
        if ch == ord('a'):
            async_mode = (async_mode + 1) % 3
        elif ch == ord('f'):
            fast_screen = (fast_screen + 1) % 2


run()
