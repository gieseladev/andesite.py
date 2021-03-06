import pytest

from andesite import AndesiteException, CPUStats, ClassLoadingStats, CompilationStats, Error, FrameStats, GCStats, MemoryCommonUsageStats, \
    MemoryManagerStats, MemoryPoolStats, MemoryStats, OSStats, PlayersStats, RuntimeSpecStats, RuntimeStats, RuntimeVMStats, RuntimeVersionStats, \
    StackFrame, Stats, ThreadStats
from andesite.transform import build_from_raw


def test_stats_load():
    raw_data = {"players": {"total": 1, "playing": 0},
                "runtime": {"uptime": 99400057, "pid": 21370, "managementSpecVersion": "2.0", "name": "21370@node3",
                            "vm": {"name": "Zing 64-Bit Tiered VM", "vendor": "Azul Systems, Inc.",
                                   "version": "11.0.1-zing_19.02.1.0-b2-product-azlinuxM-X86_64"},
                            "spec": {"name": "Java Virtual Machine Specification", "vendor": "Oracle Corporation", "version": "11"},
                            "version": {"feature": 11, "interim": 0, "update": 2, "patch": 0, "pre": None, "build": 9, "optional": "LTS"}},
                "os": {"processors": 12, "name": "Linux", "arch": "amd64", "version": "4.15.0-46-generic"},
                "cpu": {"andesite": 3.9876363152102217E-4, "system": 0.025722987996724848},
                "classLoading": {"loaded": 7149, "totalLoaded": 7149, "unloaded": 0},
                "thread": {"running": 52, "daemon": 30, "peak": 53, "totalStarted": 68},
                "compilation": {"name": "Zing 64-Bit Tiered VM", "totalTime": 108560},
                "memory": {"pendingFinalization": 0, "heap": {"init": 0, "used": 1774190592, "committed": 39512436736, "max": 39512436736},
                           "nonHeap": {"init": 0, "used": 8723456, "committed": 268435456, "max": 268435456}},
                "gc": [{"name": "GPGC New", "collectionCount": 0, "collectionTime": 0, "pools": ["GenPauseless New Gen"]},
                       {"name": "GPGC Old", "collectionCount": 0, "collectionTime": 0, "pools": ["GenPauseless Old Gen", "GenPauseless Perm Gen"]}],
                "memoryPools": [
                    {"name": "GenPauseless New Gen", "type": "HEAP",
                     "collectionUsage": {"init": 2097152, "used": 0, "committed": 0, "max": 41976594432},
                     "collectionUsageThreshold": 0,
                     "collectionUsageThresholdCount": 0,
                     "peakUsage": {"init": 2097152, "used": 1707081728, "committed": 1707081728, "max": 41976594432},
                     "usage": {"init": 2097152, "used": 1707081728, "committed": 1707081728, "max": 41976594432},
                     "usageThreshold": 0,
                     "usageThresholdCount": 0,
                     "managers": ["GPGC New"]},
                    {"name": "GenPauseless Old Gen", "type": "HEAP",
                     "collectionUsage": {"init": 0, "used": 0, "committed": 0, "max": 41976594432},
                     "collectionUsageThreshold": 0,
                     "collectionUsageThresholdCount": 0,
                     "peakUsage": {"init": 0, "used": 0, "committed": 0, "max": 41976594432},
                     "usage": {"init": 0, "used": 0, "committed": 0, "max": 41976594432},
                     "usageThreshold": 0,
                     "usageThresholdCount": 0,
                     "managers": ["GPGC Old"]},
                    {"name": "GenPauseless Perm Gen", "type": "HEAP",
                     "collectionUsage": {"init": 2097152, "used": 0, "committed": 0, "max": 41976594432},
                     "collectionUsageThreshold": 0,
                     "collectionUsageThresholdCount": 0,
                     "peakUsage": {"init": 2097152, "used": 67108864, "committed": 67108864, "max": 41976594432},
                     "usage": {"init": 2097152, "used": 67108864, "committed": 67108864, "max": 41976594432},
                     "usageThreshold": 0,
                     "usageThresholdCount": 0,
                     "managers": ["GPGC Old"]},
                    {"name": "CodeCache", "type": "NON_HEAP",
                     "collectionUsage": None,
                     "collectionUsageThreshold": None,
                     "collectionUsageThresholdCount": None,
                     "peakUsage": {"init": 0, "used": 8723456, "committed": 268435456, "max": 268435456},
                     "usage": {"init": 0, "used": 8723456, "committed": 268435456, "max": 268435456},
                     "usageThreshold": 0,
                     "usageThresholdCount": 0,
                     "managers": ["CodeCache"]}
                ],
                "memoryManagers": [{"name": "CodeCache", "pools": ["CodeCache"]}, {"name": "GPGC New", "pools": ["GenPauseless New Gen"]},
                                   {"name": "GPGC Old", "pools": ["GenPauseless Old Gen", "GenPauseless Perm Gen"]}],
                "frameStats": [{"user": "549905730099216384", "guild": "549904277108424715", "success": 0, "loss": 1500}]}

    stats = build_from_raw(Stats, raw_data)
    assert stats == Stats(
        PlayersStats(1, 0),
        RuntimeStats(99400057, 21370, "2.0", "21370@node3",
                     RuntimeVMStats("Zing 64-Bit Tiered VM", "Azul Systems, Inc.", "11.0.1-zing_19.02.1.0-b2-product-azlinuxM-X86_64"),
                     RuntimeSpecStats("Java Virtual Machine Specification", "Oracle Corporation", "11"),
                     RuntimeVersionStats(11, 0, 2, 0, None, 9, "LTS")),
        OSStats(12, "Linux", "amd64", "4.15.0-46-generic"),
        CPUStats(3.9876363152102217E-4, 0.025722987996724848),
        ClassLoadingStats(7149, 7149, 0),
        ThreadStats(52, 30, 53, 68),
        CompilationStats("Zing 64-Bit Tiered VM", 108560),
        MemoryStats(0, MemoryCommonUsageStats(0, 1774190592, 39512436736, 39512436736), MemoryCommonUsageStats(0, 8723456, 268435456, 268435456)),
        [GCStats("GPGC New", 0, 0, ["GenPauseless New Gen"]), GCStats("GPGC Old", 0, 0, ["GenPauseless Old Gen", "GenPauseless Perm Gen"])],
        [
            MemoryPoolStats("GenPauseless New Gen", "HEAP", MemoryCommonUsageStats(2097152, 0, 0, 41976594432), 0, 0,
                            MemoryCommonUsageStats(2097152, 1707081728, 1707081728, 41976594432),
                            MemoryCommonUsageStats(2097152, 1707081728, 1707081728, 41976594432), 0, 0, ["GPGC New"]),
            MemoryPoolStats("GenPauseless Old Gen", "HEAP", MemoryCommonUsageStats(0, 0, 0, 41976594432), 0, 0,
                            MemoryCommonUsageStats(0, 0, 0, 41976594432),
                            MemoryCommonUsageStats(0, 0, 0, 41976594432), 0, 0, ["GPGC Old"]),
            MemoryPoolStats("GenPauseless Perm Gen", "HEAP", MemoryCommonUsageStats(2097152, 0, 0, 41976594432), 0, 0,
                            MemoryCommonUsageStats(2097152, 67108864, 67108864, 41976594432),
                            MemoryCommonUsageStats(2097152, 67108864, 67108864, 41976594432), 0, 0, ["GPGC Old"]),
            MemoryPoolStats("CodeCache", "NON_HEAP", None, None, None,
                            MemoryCommonUsageStats(0, 8723456, 268435456, 268435456),
                            MemoryCommonUsageStats(0, 8723456, 268435456, 268435456), 0, 0, ["CodeCache"])
        ],
        [MemoryManagerStats("CodeCache", ["CodeCache"]), MemoryManagerStats("GPGC New", ["GenPauseless New Gen"]),
         MemoryManagerStats("GPGC Old", ["GenPauseless Old Gen", "GenPauseless Perm Gen"])],
        [FrameStats(549905730099216384, 549904277108424715, 0, 1500)]
    )


def test_error_load():
    raw_data = {"class": "java.lang.NullPointerException", "message": None, "suppressed": [],
                "stack": [
                    {"classLoader": "app", "moduleName": None, "moduleVersion": None,
                     "className": "andesite.node.handler.RestHandler",
                     "methodName": "lambda$trackRoutes$25", "fileName": "RestHandler.java", "lineNumber": 288,
                     "pretty": "andesite.node.handler.RestHandler.lambda$trackRoutes$25(RestHandler.java:288)"},
                    {"classLoader": "app", "moduleName": None, "moduleVersion": None,
                     "className": "io.netty.util.concurrent.SingleThreadEventExecutor$5",
                     "methodName": "run", "fileName": "SingleThreadEventExecutor.java", "lineNumber": 897,
                     "pretty": "io.netty.util.concurrent.SingleThreadEventExecutor$5.run(SingleThreadEventExecutor.java:897)"},
                    {"classLoader": "app", "moduleName": None, "moduleVersion": None,
                     "className": "io.netty.util.concurrent.FastThreadLocalRunnable",
                     "methodName": "run", "fileName": "FastThreadLocalRunnable.java", "lineNumber": 30,
                     "pretty": "io.netty.util.concurrent.FastThreadLocalRunnable.run(FastThreadLocalRunnable.java:30)"},
                    {"classLoader": None, "moduleName": "java.base", "moduleVersion": "11.0.2",
                     "className": "java.lang.Thread",
                     "methodName": "run", "fileName": "Thread.java", "lineNumber": 834,
                     "pretty": "java.base/java.lang.Thread.run(Thread.java:834)"}
                ],
                "cause": None}

    error = build_from_raw(Error, raw_data)

    assert error == Error("java.lang.NullPointerException", None, [
        StackFrame("app", None, None, "andesite.node.handler.RestHandler", "lambda$trackRoutes$25", "RestHandler.java", 288,
                   "andesite.node.handler.RestHandler.lambda$trackRoutes$25(RestHandler.java:288)"),
        StackFrame("app", None, None, "io.netty.util.concurrent.SingleThreadEventExecutor$5", "run", "SingleThreadEventExecutor.java", 897,
                   "io.netty.util.concurrent.SingleThreadEventExecutor$5.run(SingleThreadEventExecutor.java:897)"),
        StackFrame("app", None, None, "io.netty.util.concurrent.FastThreadLocalRunnable", "run", "FastThreadLocalRunnable.java", 30,
                   "io.netty.util.concurrent.FastThreadLocalRunnable.run(FastThreadLocalRunnable.java:30)"),
        StackFrame(None, "java.base", "11.0.2", "java.lang.Thread", "run", "Thread.java", 834, "java.base/java.lang.Thread.run(Thread.java:834)")
    ], [], None)


def test_error_to_python():
    raw_data = {"class": "java.lang.NullPointerException", "message": None, "suppressed": [],
                "stack": [
                    {"classLoader": "app", "moduleName": None, "moduleVersion": None,
                     "className": "andesite.node.handler.RestHandler",
                     "methodName": "lambda$trackRoutes$25", "fileName": "RestHandler.java", "lineNumber": 288,
                     "pretty": "andesite.node.handler.RestHandler.lambda$trackRoutes$25(RestHandler.java:288)"},
                    {"classLoader": "app", "moduleName": None, "moduleVersion": None,
                     "className": "io.netty.util.concurrent.SingleThreadEventExecutor$5",
                     "methodName": "run", "fileName": "SingleThreadEventExecutor.java", "lineNumber": 897,
                     "pretty": "io.netty.util.concurrent.SingleThreadEventExecutor$5.run(SingleThreadEventExecutor.java:897)"},
                    {"classLoader": "app", "moduleName": None, "moduleVersion": None,
                     "className": "io.netty.util.concurrent.FastThreadLocalRunnable",
                     "methodName": "run", "fileName": "FastThreadLocalRunnable.java", "lineNumber": 30,
                     "pretty": "io.netty.util.concurrent.FastThreadLocalRunnable.run(FastThreadLocalRunnable.java:30)"},
                    {"classLoader": None, "moduleName": "java.base", "moduleVersion": "11.0.2",
                     "className": "java.lang.Thread",
                     "methodName": "run", "fileName": "Thread.java", "lineNumber": 834,
                     "pretty": "java.base/java.lang.Thread.run(Thread.java:834)"}
                ],
                "cause": None}

    error = build_from_raw(Error, raw_data)

    with pytest.raises(AndesiteException) as exc_info:
        raise error.as_python_exception()

    assert exc_info.value.class_name == "java.lang.NullPointerException"
    assert exc_info.value.message is None
    assert exc_info.value.stack == [
        StackFrame("app", None, None, "andesite.node.handler.RestHandler", "lambda$trackRoutes$25", "RestHandler.java", 288,
                   "andesite.node.handler.RestHandler.lambda$trackRoutes$25(RestHandler.java:288)"),
        StackFrame("app", None, None, "io.netty.util.concurrent.SingleThreadEventExecutor$5", "run", "SingleThreadEventExecutor.java", 897,
                   "io.netty.util.concurrent.SingleThreadEventExecutor$5.run(SingleThreadEventExecutor.java:897)"),
        StackFrame("app", None, None, "io.netty.util.concurrent.FastThreadLocalRunnable", "run", "FastThreadLocalRunnable.java", 30,
                   "io.netty.util.concurrent.FastThreadLocalRunnable.run(FastThreadLocalRunnable.java:30)"),
        StackFrame(None, "java.base", "11.0.2", "java.lang.Thread", "run", "Thread.java", 834, "java.base/java.lang.Thread.run(Thread.java:834)")
    ]
    assert exc_info.value.suppressed == []
