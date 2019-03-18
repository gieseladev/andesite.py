"""Debug models for Andesite."""

from dataclasses import dataclass
from typing import List, Optional

from andesite.transform import RawDataType, map_build_values_from_raw, map_convert_values, map_rename_keys, seq_build_all_items_from_raw

__all__ = ["StackFrame", "Error",
           "PlayersStats", "RuntimeVMStats", "RuntimeSpecStats", "RuntimeVersionStats", "RuntimeStats", "OSStats", "CPUStats", "ClassLoadingStats",
           "ThreadStats", "CompilationStats", "MemoryCommonUsageStats", "MemoryStats", "GCStats", "MemoryPoolStats", "MemoryManagerStats",
           "FrameStats",
           "Stats"]


# noinspection PyUnresolvedReferences
@dataclass
class StackFrame:
    """

    Can be found in `Error.stack`.

    Attributes:
        class_loader (Optional[str]): name of the classloader
        module_name (Optional[str]): name of the module
        module_version (Optional[str]): version of the module
        class_name (str): name of the class
        method_name (str): name of the method
        file_name (Optional[str]): name of the source file
        line_number (Optional[int]): line in the source file
        pretty (str): pretty printed version of this frame, as it would appear on Throwable#printStackTrace
    """
    class_loader: Optional[str]
    module_name: Optional[str]
    module_version: Optional[str]
    class_name: str
    method_name: str
    file_name: Optional[str]
    line_number: Optional[int]
    pretty: str


# noinspection PyUnresolvedReferences
@dataclass
class Error:
    """Andesite error.

    Attributes:
        class_name (str): class of the error
        message (Optional[str]): message of the error
        stack (List[StackFrame]): stacktrace of the error
        cause (Optional[Error]): cause of the error
        suppressed (List[Error]): suppressed errors
    """
    class_name: str
    message: Optional[str]
    stack: List[StackFrame]
    suppressed: List["Error"]
    cause: Optional["Error"]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        seq_build_all_items_from_raw(data["stack"], StackFrame)
        seq_build_all_items_from_raw(data["suppressed"], Error)
        map_build_values_from_raw(data, cause=Error)
        map_rename_keys(data, class_name="class")


# STATISTICS


# noinspection PyUnresolvedReferences
@dataclass
class PlayersStats:
    """Players statistics sent by Andesite.

    Attributes:
        total (int): Total amount of players
        playing (int): Amount of players that are actively playing

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    total: int
    playing: int


# noinspection PyUnresolvedReferences
@dataclass
class RuntimeVMStats:
    """VM statistics.
    
    Attributes:
        name (str)
        vendor (str)
        version (str)

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    name: str
    vendor: str
    version: str


# noinspection PyUnresolvedReferences
@dataclass
class RuntimeSpecStats:
    """Spec statistics.
    
    Attributes:
        name (str)
        vendor (str)
        version (str)

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    name: str
    vendor: str
    version: str


# noinspection PyUnresolvedReferences
@dataclass
class RuntimeVersionStats:
    """Version information stats.
    
    Attributes:
        feature (int)
        interim (int)
        update (int)
        patch (int)
        pre (Optional[str])
        build (int)
        optional (str)

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    feature: int
    interim: int
    update: int
    patch: int
    pre: Optional[str]
    build: int
    optional: str


# noinspection PyUnresolvedReferences
@dataclass
class RuntimeStats:
    """Runtime statistics.
    
    Attributes:
        uptime (int)
        pid (int)
        management_spec_version (str)
        name (str)
        vm (RuntimeVMStats)
        spec (RuntimeSpecStats)
        version (RuntimeVersionStats)

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    uptime: int
    pid: int
    management_spec_version: str
    name: str
    vm: RuntimeVMStats
    spec: RuntimeSpecStats
    version: RuntimeVersionStats

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_build_values_from_raw(data, vm=RuntimeVMStats, spec=RuntimeSpecStats, version=RuntimeVersionStats)


# noinspection PyUnresolvedReferences
@dataclass
class OSStats:
    """OS statistics.
    
    Attributes:
        processors (int)
        name (str)
        arch (str)
        version (str)

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    processors: int
    name: str
    arch: str
    version: str


# noinspection PyUnresolvedReferences
@dataclass
class CPUStats:
    """CPU statistics.

    Attributes:
        andesite (float)
        system (float)

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    andesite: float
    system: float


# noinspection PyUnresolvedReferences
@dataclass
class ClassLoadingStats:
    """Class loading statistics.
    
    Attributes:
        loaded (int)
        total_loaded (int)
        unloaded (int)
    """
    loaded: int
    total_loaded: int
    unloaded: int


# noinspection PyUnresolvedReferences
@dataclass
class ThreadStats:
    """Thread statistics.
    
    Attributes:
        running (int)
        daemon (int)
        peak (int)
        total_started (int)

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    running: int
    daemon: int
    peak: int
    total_started: int


# noinspection PyUnresolvedReferences
@dataclass
class CompilationStats:
    """Compilation statistics.
    
    Attributes:
        name (str)
        total_time (int)

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    name: str
    total_time: int


# noinspection PyUnresolvedReferences
@dataclass
class MemoryCommonUsageStats:
    """Memory usage statistics.
    
    Attributes:
        init (int)
        used (int)
        committed (int)
        max (int)

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    init: int
    used: int
    committed: int
    max: int


# noinspection PyUnresolvedReferences
@dataclass
class MemoryStats:
    """Memory statistics.

    Attributes:
        pending_finalization (int)
        heap (MemoryCommonUsageStats)
        non_heap (MemoryCommonUsageStats)

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    pending_finalization: int
    heap: MemoryCommonUsageStats
    non_heap: MemoryCommonUsageStats

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_build_values_from_raw(data, heap=MemoryCommonUsageStats, non_heap=MemoryCommonUsageStats)


# noinspection PyUnresolvedReferences
@dataclass
class GCStats:
    """Garbage collection statistics.

    Attributes:
        name (str)
        collection_count (int)
        collection_time (int)
        pools (List[str])

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    name: str
    collection_count: int
    collection_time: int
    pools: List[str]


# noinspection PyUnresolvedReferences
@dataclass
class MemoryPoolStats:
    """Memory pool statistics.

    Attributes:
        name (str): Name of the pool
        type (str): Type of the pool. This is either "HEAP" or "NON_HEAP".
        collection_usage (Optional[MemoryHeapStats])
        collection_usage_threshold (Optional[int])
        collection_usage_threshold_count (Optional[int])
        peak_usage (MemoryCommonUsageStats)
        usage (MemoryCommonUsageStats)
        usage_threshold (int)
        usage_threshold_count (int)
        managers (List[str])

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    name: str
    type: str
    collection_usage: Optional[MemoryCommonUsageStats]
    collection_usage_threshold: Optional[int]
    collection_usage_threshold_count: Optional[int]
    peak_usage: MemoryCommonUsageStats
    usage: MemoryCommonUsageStats
    usage_threshold: int
    usage_threshold_count: int
    managers: List[str]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_build_values_from_raw(data, collection_usage=MemoryCommonUsageStats, peak_usage=MemoryCommonUsageStats, usage=MemoryCommonUsageStats)


# noinspection PyUnresolvedReferences
@dataclass
class MemoryManagerStats:
    """Memory manager statistics.

    Attributes:
        name (str): Name of the manager
        pools (List[str]): Memory pools

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    name: str
    pools: List[str]


# noinspection PyUnresolvedReferences
@dataclass
class FrameStats:
    """Frame statistics for a guild player.

    Attributes:
        user (int): User ID
        guild (int): Guild ID
        success (int): Amount of successful frames
        loss (int): Amount of lost frames

    See Also:
        This statistic can be found in `Stats` which is retrieved from Andesite by
        the clients. Both `AndesiteHTTP` and `AndesiteWebSocket` are able to get them.
    """
    user: int
    guild: int
    success: int
    loss: int

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_convert_values(data, user=int, guild=int)

    @classmethod
    def __transform_output__(cls, data: RawDataType) -> None:
        map_convert_values(data, user=str, guild=str)


# noinspection PyUnresolvedReferences
@dataclass
class Stats:
    """Statistics sent by Andesite

    Attributes:
        players (PlayersStats): Player statistics
        runtime (RuntimeStats): Runtime statistics
        os (OSStats): OS statistics
        cpu (CPUStats): CPU statistics
        class_loading (ClassLoadingStats): Class loading statistics
        thread (ThreadStats): Thread statistics
        compilation (CompilationStats): Compilation statistics
        memory (MemoryStats): Memory statistics
        gc (List[GCStats]): GC statistics
        memory_pools (List[MemoryPoolStats]): Memory pool statistics
        memory_managers (List[MemoryManagerStats]): Memory manager statistics
        frame_stats (List[FrameStats]): Frame statistics
    """

    players: PlayersStats
    runtime: RuntimeStats
    os: OSStats
    cpu: CPUStats
    class_loading: ClassLoadingStats
    thread: ThreadStats
    compilation: CompilationStats
    memory: MemoryStats
    gc: List[GCStats]
    memory_pools: List[MemoryPoolStats]
    memory_managers: List[MemoryManagerStats]
    frame_stats: List[FrameStats]

    @classmethod
    def __transform_input__(cls, data: RawDataType) -> None:
        map_build_values_from_raw(data,
                                  players=PlayersStats, runtime=RuntimeStats, os=OSStats, cpu=CPUStats, class_loading=ClassLoadingStats,
                                  thread=ThreadStats, compilation=CompilationStats, memory=MemoryStats,
                                  )
        seq_build_all_items_from_raw(data["gc"], GCStats)
        seq_build_all_items_from_raw(data["memory_pools"], MemoryPoolStats)
        seq_build_all_items_from_raw(data["memory_managers"], MemoryManagerStats)
        seq_build_all_items_from_raw(data["frame_stats"], FrameStats)
