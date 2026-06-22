//typing rules for functions and applications

fn apply_twice<F>(f: F, x: i32) -> i32
where F: Fn(i32) -> i32,
{
    f(f(x))
}

fn multiply(v: i32) -> i32 {
    v * v
}

//Never type
// fn spread_panic() -> ! {  // Rust's Never type
//     panic!("boom");
//     //let x = 2;
//     //x
// }

//the Dynamic Type
use std::any::Any;

fn accept_anything(value: &dyn Any) {
    if let Some(num) = value.downcast_ref::<i32>() {
        println!("Got number: {}", num);
    }
}

//explicit opt-in
use rust_decimal::Decimal;

// ABC equivalent — trait defines the contract
trait PaymentProcessor {
    fn process_payment(&self, amount: Decimal) -> String;
    fn refund(&self, transaction_id: &str);
}

struct StripeProcessor;

impl PaymentProcessor for StripeProcessor {
    fn process_payment(&self, amount: Decimal) -> String {
        "a string".to_string()
    }

    fn refund(&self, transaction_id: &str) {
        // no-op
    }
}

fn identity<T>(x: T) -> T {
    x
}

fn main(){
    //apply_twice
    let x: i32 = 2;
    let result = apply_twice(multiply, x);
    println!("Result: {}", result);

    //Never type
//     spread_panic();

    //Dynamic type
    accept_anything(&42);
    accept_anything(&"hello");
    accept_anything(&vec![1,2,3]);
    let result = identity(42);
    let text = identity("hello");
    let result = identity::<i32>(42);
}

