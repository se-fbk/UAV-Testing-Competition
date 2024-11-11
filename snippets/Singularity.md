# Run test generation with singularity

## Requirements

singularity > 3.8

## Build image

In subfolder snippets, run the following commnad

```bash
singularity build --fakeroot singularityUAV.simg singularityUAV.def
```

## <a name="run"></a>  Run test generation

If not already present, create required folders:
- generated_tests
- logs

To run test generation for mission in file case_studies/mission1.yaml with budget 1, execute

```bash
singularity exec --fakeroot --writable --bind .:/src/generator:rw  singularityUAV.simg  sh /src/generator/initialize_env.sh sh /src/generator/run_generation.sh case_studies/mission1.yaml 1
```

The script execute python command

```bash
python3 cli.py generate case_studies/mission1.yaml 1
```

## Manual run on a slurm node

To run on the cluster, first login on a node. For instance

```bash
srun  --mem=32g --cpus-per-task=16 -w node91 -p identical-9  --pty bash -i
```

Load singularity module, if needed 

```bash
module load singularity/3.8.7
```

[Run](#run) test generation. 







