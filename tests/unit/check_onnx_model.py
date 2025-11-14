import onnx

model = onnx.load('depth_anything_v2_vits.onnx')
print(f'ONNX IR version: {model.ir_version}')
print(f'Opset version: {model.opset_import[0].version}')
print(f'Producer: {model.producer_name} {model.producer_version}')
print('\nInputs:')
for inp in model.graph.input:
    shape = [d.dim_value if d.dim_value else 'dynamic' for d in inp.type.tensor_type.shape.dim]
    print(f'  {inp.name}: {shape}')
print('\nOutputs:')
for out in model.graph.output:
    shape = [d.dim_value if d.dim_value else 'dynamic' for d in out.type.tensor_type.shape.dim]
    print(f'  {out.name}: {shape}')
print(f'\nTotal nodes: {len(model.graph.node)}')
