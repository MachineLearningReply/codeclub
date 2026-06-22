package main

import "fmt"
import "context"

// Top Type

// any is Go's top type (alias for interface{})
// every type is a subtype of any
func describe(v any) {
	fmt.Printf("%v (%T)\n", v, v)
}

//go interface (structural)
type CacheData struct {
    Key string
    Value any
}

type CacheInterface interface {
    AGet(ctx context.Context, key string) (CacheData, error)
    ASet(ctx context.Context, value any) error
}

type RedisCache struct {}

func (r *RedisCache) AGet(ctx context.Context, key string) (CacheData, error) {
    return CacheData{Key: key, Value: "value"}, nil
}

func (r *RedisCache) ASet(ctx context.Context, entry any) error {
	return nil
}

func run(ctx context.Context, cache CacheInterface) error {
	data, err := cache.AGet(ctx, "a-key")
	fmt.Printf("%v\n", data)
	if err!= nil {
	    return err
    }
    return nil
}

func main() {
    // top type
	describe(42)
	describe("hello")
	describe(true)
}
