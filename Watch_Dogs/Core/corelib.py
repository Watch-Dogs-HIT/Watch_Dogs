#!/usr/bin/env python
# encoding:utf-8

"""
进程检测核心功能实现

主要包括
- 总体CPU占用率
- 总体内存占用率
- 总体网络上下载速度

reference   :   https://www.jianshu.com/p/deb0ed35c1c2
reference   :   https://www.kernel.org/doc/Documentation/filesystems/proc.txt
"""

from time import sleep, time

calc_func_interval = 2
prev_cpu_work_time = 0
prev_cpu_total_time = 0
prev_net_receive_byte = 0
prev_net_send_byte = 0
prev_net_time = 0


def get_total_cpu_time():
    """获取总cpu时间 - /proc/stat"""

    """    
    /proc/stat 
        kernel/system statistics.  Varies with architecture.  Common entries include:

        cpu 10132153 290696 3084719 46828483 16683 0 25195 0 175628 0
        cpu0 1393280 32966 572056 13343292 6130 0 17875 0 23933 0
        
        The  amount  of  time,  measured in units of USER_HZ (1/100ths of a second on most architectures, 
        use sysconf(_SC_CLK_TCK) to obtain the right value), that the system ("cpu" line) or 
        the specific CPU ("cpuN" line) spent in various states:

        user   (1) Time spent in user mode.
      
        nice   (2) Time spent in user mode with low priority (nice).
      
        system (3) Time spent in system mode.
      
        idle   (4) Time spent in the idle task.  This value should be USER_HZ times the second entry in the /proc/uptime pseudo-file.
      
        iowait (since Linux 2.5.41) (5) Time waiting for I/O to complete.  
        
        This value is not reliable, for the following reasons:
        1. The CPU will not wait for I/O to complete; iowait is the time that a task is waiting for I/O to complete.  
        When a CPU goes into idle state for outstanding task I/O, another task will be scheduled on this CPU.
    
        2. On a multi-core CPU, the task waiting for I/O to complete is not running on any CPU, so the iowait of each CPU is difficult to calculate.
    
        3. The value in this field may decrease in certain conditions.
    
        irq (since Linux 2.6.0-test4) (6) Time servicing interrupts.
    
        softirq (since Linux 2.6.0-test4) (7) Time servicing softirqs.
    
        steal (since Linux 2.6.11) (8) Stolen time, which is the time spent in other operating systems when running in a virtualized environment
    
        guest (since Linux 2.6.24) (9) Time spent running a virtual CPU for guest operating systems under the control of the Linux kernel.
    
        guest_nice (since Linux 2.6.33) (10) Time spent running a niced guest (virtual CPU for guest operating systems under the control of the Linux kernel).

        page 5741 1808
        The number of pages the system paged in and the number that were paged out (from disk).

        swap 1 0
        The number of swap pages that have been brought in and out.

        intr 1462898
        This  line  shows  counts  of  interrupts  serviced since boot time, for each of the possible system interrupts.
        The first column is the total of all interrupts serviced including unnumbered architecture specific
        interrupts; each subsequent column is the total for that particular numbered interrupt.  
        Unnumbered interrupts are not shown, only summed into the total.

        disk_io: (2,0):(31,30,5764,1,2) (3,0):...
        (major,disk_idx):(noinfo, read_io_ops, blks_read, write_io_ops, blks_written)
        (Linux 2.4 only)

        ctxt 115315
        The number of context switches that the system underwent.

        btime 769041601
        boot time, in seconds since the Epoch, 1970-01-01 00:00:00 +0000 (UTC).

        processes 86031
        Number of forks since boot.

        procs_running 6
        Number of processes in runnable state.  (Linux 2.5.45 onward.)

        procs_blocked 2
        Number of processes blocked waiting for I/O to complete.  (Linux 2.5.45 onward.)

        softirq 229245889 94 60001584 13619 5175704 2471304 28 51212741 59130143 0 51240672
        This line shows the number of softirq for all CPUs.  The first column is the total of all softirqs and 
        each subsequent column is the total for particular softirq.  (Linux 2.6.31 onward.)
    """

    # CPU的占有率计算公式
    # workTime  =   user + nice + system;
    # totalTime =   return user + nice + system + idle + iowait + irq + softirq + steal;
    # cpuPercent = (currentWorkTime - prevWorkTime) / (currentTotalTime - prevTotalTime)

    #
    # sum everything up (except guest and guestnice since they are already included
    # in user and nice, see http://unix.stackexchange.com/q/178045/20626)

    with open("/proc/stat", "r") as cpu_stat:
        total_cpu_time = cpu_stat.readline().replace('cpu', '').strip()
        user, nice, system, idle, iowait, irq, softirq, steal, guest, guestnice = map(int, total_cpu_time.split(' '))
        return user + nice + system + idle + iowait + irq + softirq + steal, user + nice + system


def calc_cpu_percent(interval=calc_func_interval):
    """计算CPU总占用率 (返回的是百分比)"""
    # 两次调用之间的间隔最好不要小于2s,否则可能会为0
    global prev_cpu_work_time, prev_cpu_total_time
    if prev_cpu_work_time == 0:  # 未初始化
        prev_cpu_total_time, prev_cpu_work_time = get_total_cpu_time()
        sleep(interval)
    current_total_time, current_work_time = get_total_cpu_time()
    cpu_percent = (current_work_time - prev_cpu_work_time) * 100.0 / (current_total_time - prev_cpu_total_time)
    prev_cpu_total_time, prev_cpu_work_time = current_total_time, current_work_time
    return cpu_percent


def get_mem_info():
    """获取内存信息 - /proc/meminfo"""

    """
    /proc/meminfo
    This  file  reports statistics about memory usage on the system.  It is used by free(1) to report the amount of free
     and used memory (both physical and swap) on the system as well as the shared memory and buffers used by
    the kernel.  Each line of the file consists of a parameter name, followed by a colon, the value of the parameter, 
    and an option unit of measurement (e.g., "kB").  The list below describes the parameter names and the for‐
    mat  specifier  required to read the field value.  Except as noted below, all of the fields have been present since 
    at least Linux 2.6.0.  Some fields are displayed only if the kernel was configured with various options;
    those dependencies are noted in the list.

    MemTotal %lu
        Total usable RAM (i.e., physical RAM minus a few reserved bits and the kernel binary code).

    MemFree %lu
        The sum of LowFree+HighFree.

    MemAvailable %lu (since Linux 3.14)
        An estimate of how much memory is available for starting new applications, without swapping.

    Buffers %lu
        Relatively temporary storage for raw disk blocks that shouldn't get tremendously large (20MB or so).

    Cached %lu
        In-memory cache for files read from the disk (the page cache).  Doesn't include SwapCached.

    SwapCached %lu
        Memory that once was swapped out, is swapped back in but still also is in the swap file.  
        (If memory pressure is high, these pages don't need to be swapped out again because they are  already  
        in  the  swap  file. This saves I/O.)

    Active %lu
        Memory that has been used more recently and usually not reclaimed unless absolutely necessary.

    Inactive %lu
        Memory which has been less recently used.  It is more eligible to be reclaimed for other purposes.

    Active(anon) %lu (since Linux 2.6.28)
        [To be documented.]

    Inactive(anon) %lu (since Linux 2.6.28)
        [To be documented.]

    Active(file) %lu (since Linux 2.6.28)
        [To be documented.]

    Inactive(file) %lu (since Linux 2.6.28)
        [To be documented.]

    Unevictable %lu (since Linux 2.6.28)
        (From Linux 2.6.28 to 2.6.30, CONFIG_UNEVICTABLE_LRU was required.)  [To be documented.]

    Mlocked %lu (since Linux 2.6.28)
        (From Linux 2.6.28 to 2.6.30, CONFIG_UNEVICTABLE_LRU was required.)  [To be documented.]

    HighTotal %lu
     (Starting with Linux 2.6.19, CONFIG_HIGHMEM is required.)  Total amount of highmem.  
     Highmem is all memory above ~860MB of physical memory.  Highmem areas are for use by user-space programs, 
     or for the page cache.
     The kernel must use tricks to access this memory, making it slower to access than lowmem.

    HighFree %lu
        (Starting with Linux 2.6.19, CONFIG_HIGHMEM is required.)  Amount of free highmem.

    LowTotal %lu
        (Starting with Linux 2.6.19, CONFIG_HIGHMEM is required.)  Total amount of lowmem.  Lowmem is memory which can be used for everything that highmem can be used for, but it is also available for the kernel's use for
        its own data structures.  Among many other things, it is where everything from Slab is allocated.  Bad things happen when you're out of lowmem.

    LowFree %lu
        (Starting with Linux 2.6.19, CONFIG_HIGHMEM is required.)  Amount of free lowmem.

    MmapCopy %lu (since Linux 2.6.29)
        (CONFIG_MMU is required.)  [To be documented.]

    SwapTotal %lu
        Total amount of swap space available.

    SwapFree %lu
        Amount of swap space that is currently unused.

    Dirty %lu
        Memory which is waiting to get written back to the disk.

    Writeback %lu
        Memory which is actively being written back to the disk.

    AnonPages %lu (since Linux 2.6.18)
        Non-file backed pages mapped into user-space page tables.

    Mapped %lu
        Files which have been mapped into memory (with mmap(2)), such as libraries.

    Shmem %lu (since Linux 2.6.32)
        Amount of memory consumed in tmpfs(5) filesystems.

    Slab %lu
        In-kernel data structures cache.  (See slabinfo(5).)

    SReclaimable %lu (since Linux 2.6.19)
        Part of Slab, that might be reclaimed, such as caches.

    SUnreclaim %lu (since Linux 2.6.19)
        Part of Slab, that cannot be reclaimed on memory pressure.

    KernelStack %lu (since Linux 2.6.32)
        Amount of memory allocated to kernel stacks.

    PageTables %lu (since Linux 2.6.18)
        Amount of memory dedicated to the lowest level of page tables.

    Quicklists %lu (since Linux 2.6.27)
        (CONFIG_QUICKLIST is required.)  [To be documented.]

    NFS_Unstable %lu (since Linux 2.6.18)
        NFS pages sent to the server, but not yet committed to stable storage.

    Bounce %lu (since Linux 2.6.18)
        Memory used for block device "bounce buffers".

    WritebackTmp %lu (since Linux 2.6.26)
        Memory used by FUSE for temporary writeback buffers.

    CommitLimit %lu (since Linux 2.6.10)
        This is the total amount of memory currently available to be allocated on the system, expressed in kilobytes.  
        This limit is adhered to only if strict overcommit accounting is enabled (mode 2 in /proc/sys/vm/over‐
        commit_memory).  The limit is calculated according to the formula described under /proc/sys/vm/overcommit_memory. 
         For further details, see the kernel source file Documentation/vm/overcommit-accounting.

    Committed_AS %lu
        The amount of memory presently allocated on the system.  The committed memory is a sum of all of the memory 
        which has been allocated by processes, even if it has not been "used" by them as of yet.  A process which
        allocates 1GB of memory (using malloc(3) or similar), but touches only 300MB of that memory will show up as
         using only 300MB of memory even if it has the address space allocated for the entire 1GB.

        This 1GB is memory which has been "committed" to by the VM and can be used at any time by the allocating application.  With strict overcommit enabled on the system (mode 2 in /proc/sys/vm/overcommit_memory), allo‐
        cations which would exceed the CommitLimit will not be permitted.  This is useful if one needs to guarantee that processes will not fail due to lack of memory once that memory has been successfully allocated.

    VmallocTotal %lu
        Total size of vmalloc memory area.

    VmallocUsed %lu
        Amount of vmalloc area which is used.

    VmallocChunk %lu
        Largest contiguous block of vmalloc area which is free.

    HardwareCorrupted %lu (since Linux 2.6.32)
        (CONFIG_MEMORY_FAILURE is required.)  [To be documented.]

    AnonHugePages %lu (since Linux 2.6.38)
        (CONFIG_TRANSPARENT_HUGEPAGE is required.)  Non-file backed huge pages mapped into user-space page tables.

    ShmemHugePages %lu (since Linux 4.8)
        (CONFIG_TRANSPARENT_HUGEPAGE is required.)  Memory used by shared memory (shmem) and tmpfs(5) allocated with huge pages

    ShmemPmdMapped %lu (since Linux 4.8)
        (CONFIG_TRANSPARENT_HUGEPAGE is required.)  Shared memory mapped into user space with huge pages.

    CmaTotal %lu (since Linux 3.1)
        Total CMA (Contiguous Memory Allocator) pages.  (CONFIG_CMA is required.)

    CmaFree %lu (since Linux 3.1)
        Free CMA (Contiguous Memory Allocator) pages.  (CONFIG_CMA is required.)

    HugePages_Total %lu
        (CONFIG_HUGETLB_PAGE is required.)  The size of the pool of huge pages.

    HugePages_Free %lu
        (CONFIG_HUGETLB_PAGE is required.)  The number of huge pages in the pool that are not yet allocated.

    HugePages_Rsvd %lu (since Linux 2.6.17)
        (CONFIG_HUGETLB_PAGE is required.)  This is the number of huge pages for which a commitment to allocate from 
        the pool has been made, but no allocation has yet been made.  These reserved huge pages  guarantee  that
        an application will be able to allocate a huge page from the pool of huge pages at fault time.

    HugePages_Surp %lu (since Linux 2.6.24)
        (CONFIG_HUGETLB_PAGE  is  required.)   This is the number of huge pages in the pool above the value in 
        /proc/sys/vm/nr_hugepages.  The maximum number of surplus huge pages is controlled by /proc/sys/vm/nr_overcom‐
        mit_hugepages.

    Hugepagesize %lu
        (CONFIG_HUGETLB_PAGE is required.)  The size of huge pages.

    DirectMap4k %lu (since Linux 2.6.27)
        Number of bytes of RAM linearly mapped by kernel in 4kB pages.  (x86.)

    DirectMap4M %lu (since Linux 2.6.27)
        Number of bytes of RAM linearly mapped by kernel in 4MB pages.  (x86 with CONFIG_X86_64 or CONFIG_X86_PAE enabled.)

    DirectMap2M %lu (since Linux 2.6.27)
        Number of bytes of RAM linearly mapped by kernel in 2MB pages.  (x86 with neither CONFIG_X86_64 nor CONFIG_X86_PAE enabled.)

    DirectMap1G %lu (since Linux 2.6.27)
        (x86 with CONFIG_X86_64 and CONFIG_X86_DIRECT_GBPAGES enabled.)
    """

    with open("/proc/meminfo", "r") as mem_info:
        MemTotal = mem_info.readline().split(":")[1].strip().strip("kB")
        MemFree = mem_info.readline().split(":")[1].strip().strip("kB")
        MemAvailable = mem_info.readline().split(":")[1].strip().strip("kB")
        print MemTotal
        return map(int, [MemTotal, MemFree, MemAvailable])


def calc_mem_percent():
    """计算系统内存占用率 (返回的是百分比)"""
    # memoryPercent = (total - available) * 100.0 / total
    # 注意，当前系统使用的内存是由内存总量total减去可用内存aviailable的值来计算的，不能用
    # memoryPercent = used * 100.0 / total
    # 因为 used 的值不包括一些被内核占用并且永不释放的缓存内存，如果用 used 的方式来计算内存百分比，
    # 会发现最终计算的结果会比实际占用的内存小 15% 左右。
    MemTotal, MemFree, MemAvailable = get_mem_info()
    mem_percent = (MemTotal - MemAvailable) * 100.0 / MemTotal
    return mem_percent


def get_net_dev_data():
    """获取系统网络数据 -  /proc/net/dev"""

    """
    The dev pseudo-file contains network device status information.  This gives the number of received and sent packets, 
    the number of errors and collisions and other basic statistics.  These are used by the ifconfig(8) program
    to report device status.  The format is:

        Inter-|   Receive                                                |  Transmit
        face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
        lo: 2776770   11307    0    0    0     0          0         0  2776770   11307    0    0    0     0       0          0
        eth0: 1215645    2751    0    0    0     0          0         0  1782404    4324    0    0    0   427       0          0
        ppp0: 1622270    5552    1    0    0     0          0         0   354130    5669    0    0    0     0       0          0
        tap0:    7714      81    0    0    0     0          0         0     7714      81    0    0    0     0       0          0

    """
    receive_bytes = 0
    send_bytes = 0
    with open("/proc/net/dev", "r") as net_dev:
        for line in net_dev.readlines():
            if line.count(":") and not line.count("lo"):
                dev_data = map(int, filter(lambda x: x, line.split(":", 2)[1].strip().split(" ")))
                receive_bytes += dev_data[0]
                send_bytes += dev_data[8]

    return receive_bytes, send_bytes


def calc_net_speed(interval=calc_func_interval):
    """
    计算网络速度
    :return: [上传速度,下载速度] (单位为Kbps)
    """
    global prev_net_receive_byte, prev_net_send_byte, prev_net_time
    if prev_net_receive_byte == 0:  # 未初始化
        prev_net_receive_byte, prev_net_send_byte = get_net_dev_data()
        prev_net_time = time()
        sleep(interval)
    current_net_receive_byte, current_net_send_byte = get_net_dev_data()
    current_net_time = time()
    download_speed = (current_net_receive_byte - prev_net_receive_byte) / 1024.0 / (current_net_time - prev_net_time)
    upload_speed = (current_net_send_byte - prev_net_send_byte) / 1024.0 / (current_net_time - prev_net_time)
    prev_net_receive_byte, prev_net_send_byte = current_net_receive_byte, current_net_send_byte
    prev_net_time = current_net_time
    return download_speed, upload_speed


if __name__ == '__main__':
    while 1:
        sleep(2)
        print calc_net_speed()
