# Kubernetes deployment

These manifests deploy the application to AKS and expose it through Azure Application Gateway Ingress Controller.

Apply the namespace first:

```bash
kubectl apply -f deployments/namespace.yaml
```

Create the real secret from local values. Do not commit real secrets to Git.

```bash
kubectl create secret generic dnstofd-secrets \
  --namespace dnstofd \
  --from-literal=DB_CONNECTION_STRING='postgresql+asyncpg://<user>:<password>@<server>.postgres.database.azure.com:5432/<database>?ssl=require' \
  --from-literal=BLOB_STORAGE_CONNECTION_STRING='<storage-connection-string>' \
  --from-literal=BLOB_STORAGE_ACCOUNT_URL='https://<storage-account>.blob.core.windows.net/' \
  --from-literal=AZURE_TENANT_ID='<tenant-id>' \
  --from-literal=AZURE_CLIENT_ID='<client-id>' \
  --from-literal=AZURE_CLIENT_SECRET='<client-secret>'
```

Deploy the workload:

```bash
kubectl apply -f deployments/deployment.yaml
kubectl apply -f deployments/service.yaml
kubectl apply -f deployments/ingress.yaml
```

Check the rollout and ingress:

```bash
kubectl get pods,svc,ingress -n dnstofd
kubectl rollout status deployment/dns-to-fd -n dnstofd
curl http://dnstofd.germanywestcentral.cloudapp.azure.com/healthz
```

Traffic path:

```text
DNS name -> App Gateway public IP -> App Gateway listener/rule -> AKS Service -> Pod port 8000
```
