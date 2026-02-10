# collector_service/tests/debug_timing.py
# Author: Andrew Fox
# Run with: python -m collector_service.tests.debug_timing

import time
from collector_service.collector.cpu_collector import CPUCollector
from collector_service.collector.ram_collector import RAMCollector
from collector_service.collector.disk_collector import DiskCollector
from collector_service.collector.gpu_collector import GPUCollector

def profile_collector(name, collector_func, iterations=10):
    times = []
    for i in range(iterations):
        start = time.perf_counter()
        data = collector_func()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        print(f"{name} iteration {i+1}: {elapsed:.2f}ms")
        time.sleep(0.1)
    
    avg = sum(times) / len(times)
    max_time = max(times)
    print(f"\n{name} - Average: {avg:.2f}ms, Max: {max_time:.2f}ms\n")

if __name__ == "__main__":
    print("=== Profiling Collectors ===\n")
    
    profile_collector("CPU", CPUCollector.get_cpu_data)
    profile_collector("RAM", RAMCollector.get_ram_data)
    profile_collector("GPU", GPUCollector.get_gpu_data)
    profile_collector("Disk", DiskCollector.get_disk_data)
    
    print("\n=== Testing all together ===")
    for i in range(10):
        total_start = time.perf_counter()
        
        cpu_start = time.perf_counter()
        cpu_data = CPUCollector.get_cpu_data()
        cpu_time = (time.perf_counter() - cpu_start) * 1000
        
        ram_start = time.perf_counter()
        ram_data = RAMCollector.get_ram_data()
        ram_time = (time.perf_counter() - ram_start) * 1000
        
        gpu_start = time.perf_counter()
        gpu_data = GPUCollector.get_gpu_data()
        gpu_time = (time.perf_counter() - gpu_start) * 1000
        
        disk_start = time.perf_counter()
        disk_data = DiskCollector.get_disk_data()
        disk_time = (time.perf_counter() - disk_start) * 1000
        
        total_time = (time.perf_counter() - total_start) * 1000
        
        print(f"Iteration {i+1}: CPU={cpu_time:.2f}ms, RAM={ram_time:.2f}ms, "
              f"GPU={gpu_time:.2f}ms, Disk={disk_time:.2f}ms, TOTAL={total_time:.2f}ms")
        
        time.sleep(1)