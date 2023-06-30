import time
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis_om import get_redis_connection, HashModel
from fastapi.background import BackgroundTasks


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins='[http://localhost:3000]',
    allow_methods=['*'],
    allow_headers=['*']
)

redis = get_redis_connection(
    host='redis-14006.c55.eu-central-1-1.ec2.cloud.redislabs.com',
    port=14006,
    password='6Xk9CQxHFkS5LaZonYer6yz0QsLdMmVw',
    decode_responses=True
)


class ProductOrder(HashModel):
    product_id: str
    quantity: int

    class Meta:
        database = redis


class Order(HashModel):
    product_id: str
    price: float
    fee: float
    total: float
    quantity: int
    status: str

    class Meta:
        database = redis


@app.post('/orders')
def create(productOrder: ProductOrder, background_tasks: BackgroundTasks):
    req = requests.get(
        f'http://localhost:8001/product/{productOrder.product_id}')
    product = req.json()
    fee = product['price'] * 0.2

    order = Order(
        product_id=productOrder.product_id,
        price=product['price'],
        fee=fee,
        total=product['price'] + fee,
        quantity=productOrder.quantity,
        status='pending'
    )

    order.save()

    background_tasks.add_task(order_complete, order)
    return order


def format(pk: str):
    order = Order.get(pk)
    return {
        'id': order.pk,
        'product_id': order.product_id,
        'fee': order.fee,
        'total': order.total,
        'status': order.status,
        'quantity': order.quantity
    }


@app.get('/orders/{pk}')
def get(pk: str):
    return format(pk)


@app.get('/orders')
def get_all():
    return [format(pk) for pk in Order.all_pks()]


def order_complete(order: Order):
    time.sleep(5)
    order.status = 'completed'
    order.save()
    redis.xadd(name='order-completed', fields=order.dict())
# @app.delete('/product/{pk}')
# def delete(pk: str):
#     return Product.delete(pk)
