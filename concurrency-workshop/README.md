# Concurrency Modeling in Python


## Day 1: Preemptive Concurrency: Threads, Processes, and GIL


### Baseline

####  Sequential Execution
Generally how code is executed

#### OS Scheduler, Threads, Processes
- OS Scheduler behaviour for sequential code in one python program vs other programs
- Thread as an execution unit within a process, sharing memory, FDs, etc. (generally shared address space)
- Multiple threads and shared memory (main thread vs the rest)
- Process with isolated stack (separate address spaces)

#### Concurrency vs Parallelism

- Also describe preemptive concurrency vs cooperative concurrency

#### Threads in Python
- Creation, launching, and finishing a thread (threading.Thread vs ThreadPoolExecutor)
- Demonstrate thread creation live inside /proc

#### Race Conditions and Locking in Threads
- Why race exists
- Demonstrate data corruption
- Demonstrate locking as prevention


#### Blocking Calls
- We should be able to switch between tasks if waiting is involved
- Demonstrate preemptive scheduling via sleeping

#### GIL
- CPython GIL
- Relation to Python bytecode 
- Releasing vs Acquiring GIL
- Current CPython interpreter thread context switching every 5ms
- Releasers: C API level, disk IO, network IO, and other blocking syscalls, sleeping, numpy, PyTorch

#### GIL and Threads
- Worse performance with CPU sequential and CPU bound code
- Demonstrate GIL release during blocking syscalls or IO
- Clarify that a thread releasing GIL may reacquire it is merely "preempted" 
- No proper CPU time distribution exists 

#### Multiprocessing in Python
- Creation of child processes via os.fork
- os.fork vs os.spawn
- Demonstrate with multiprocessing library for python processes (multiprocessing.Process vs ProcessPoolExecutor)
- Subprocess for child processes (different executables)
- Live demonstration in the /proc file system
- IPC
- Subinterpreters 
- Per-interpreter GIL

##### Final Note: multiprocessing is not always required since most of the day-to-day tasks include some sort of blocking calls. This, however, could consequently create thousands of threads, which has a lot of overhead for memory and scheduling. Although we can, of course, multiplex computations over a couple of threads, we should be able to switch between computations/tasks deliberately without the overhead of thread switching and shared memory management at all. Therefore, 1 thread and thousands of computations that involve some blocking => Cooperative Concurrency


## Day 2: Cooperative Concurrency: Generators  -> classic coroutines  ->  Native Coroutines 

#### Iterators 
- What are iterators vs iterables?
- How to create iterators?
- collections.abc.Iterator Protocol

#### Generators as suspendable computation
- What is a Generator? Suspension and saving of execution frame (what is a frame?), instruction position, evaluation stack, and maintenance of exception state 
- Iterator vs Generator
- How to create a generator? 
- Function vs generator
- Driving a generator (next, send)
- throw/close
- StopIteration and GeneratorExit
- CPython bytecode

#### Tiny cooperative scheduler

#### Manual inter-generator delegation

#### yield from 

#### Classic Coroutines

#### Native Coroutines as an intra-thread execution context
- await
- awaitables vs Coroutine 
- Coroutine and Generator protocols from collections.abc


#### Inter-coroutine delegation 
- custom \_\_await\_\_  returning an iterator
- add a coro with await and drive custom \_\_await\_\_ 


#### Toy Task, Event Loop

#### IO multiplexing by OS Kernel 
- FD and sockets
- Epoll demonstration (macOS has kqueue)
- This allows one thread to wait for many I/O sources (usually via FDs and sockets)
- How does OS do that? Software and hardware traps eventually communicate that an FD/socket (read/recv for e.g.) can be performed

#### Hold my (async)IO!

- Coroutine vs asyncio Task vs Future, Callback, Event Loop, Cancellation
- Demonstrate all live (asyncio.create_task vs actually awaiting)


#### Demonstrate cooperative interleaving of tasks
- start with forced sequential execution 
- add use asyncio.sleep() to demonstrate interleaving and event loop scheduling
- 

#### Unstructured vs Structured Concurrency
- definitions and goals

#### Unstructured with asyncio.create_task
- completion is nondeterministic
- task cancellation in relation to generator.throw()
- asyncio.shield(task) to avoid exception propagation

#### What is so unstructured here?
- who receives exceptions? 
- who was responsible for awaiting this task?
- who cleans it up?
- What if main() exits?
- What if the parent/caller gets cancelled?

add structuring: parents are explicit and lifetimes are bounded 

#### A bit more structure with asyncio.gather()
- return_exceptions=False
- wait vs gather 

#### (Fully) Structured with asyncio.TaskGroup

- Also touch upon ExceptionGroup

#### Threads and Coroutines: a strange marriage
- Some calls can still block the main event-loop thread 
- asyncio.to_thread()
- loop.run_in_executor()
- executor: ThreadPoolExecutor (shared memory address space) vs ProcessPoolExecutor (separate memory address space)
- Allows for exception propagation
- ProcessPoolExecutor still adds IPC overhead, picklability 


#### Final Takeaways:
- Understand intra-thread, inter-thread, and multi process concurrency
- What is the execution code? Who schedules it? What suspends execution? Is memory shared? Who owns the execution unit's lifetime? How do failures and cancellations propagate?
- When to use which

## What is next?
- Free-threaded CPython
- Parallelism and Concurrency in Rust 
