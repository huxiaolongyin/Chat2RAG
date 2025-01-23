from time import perf_counter


class MetricsRecorder:
    def __init__(self):
        self.start_time = perf_counter()
        self.metrics = {}

    def record_step(self, step_name: str):
        self.metrics[step_name] = perf_counter() - self.start_time

    def get_total_time(self):
        return perf_counter() - self.start_time
