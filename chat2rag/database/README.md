使用 `alembic` 进行初始化和迁移


# 更新
```bash
alembic revision --autogenerate -m "add flow_data table"
```

# 升版本
```bash
alembic upgrade head
```