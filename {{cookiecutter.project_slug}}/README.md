# {{cookiecutter.project_name}}

The setup script has been tested and will checkout, compile and run the {{cookiecutter.project_slug}} (NEMO 4.2.2) code on: ARCHER2 for Cray-MPICH and GNU-MPICH, and Anemone for iFort.


<img width="541" alt="Screenshot 2025-06-19 at 16 40 30" src="https://github.com/user-attachments/assets/1c681919-c59d-4750-a92e-9e0b9a0d5411" />

[Documentation](https://noc-msm.github.io/{{cookiecutter.project_slug}}/)

## Quick Start:
On ARCHER2
```
git clone git@github.com:NOC-MSM/{{cookiecutter.project_slug}}.git
./{{cookiecutter.project_slug}}/scripts/setup/{{cookiecutter.project_slug}}_setup -p $PWD/{{cookiecutter.project_slug}}_RUNS  -r $PWD/{{cookiecutter.project_slug}} -n 4.2.2 -x 2 -m archer2 -a mpich -c gnu
cd {{cookiecutter.project_slug}}_RUNS/nemo/cfgs/{{cookiecutter.project_slug}}//
cp -rP EXPREF EXP_MYRUN
cd EXP_MYRUN
ln -s ../INPUTS/domain_cfg_mes.nc domain_cfg.nc
```
or if using ANEMONE, replace use options:
```
-m anemone -a impi -c ifort
```
Edit the project code and options in  `runscript_continuous.slurm` then:
```
sbatch runscript.slurm -y 1979 -s 1
```
This will produce a 5 day mean output from the beginning of 1979. The run should take 15 minutes to complete once in the machine.

### Forcing data:

[{{cookiecutter.project_slug}}](https://gws-access.jasmin.ac.uk/public/jmmp/{{cookiecutter.project_slug}}/)

_this is automatically transferred when the setup script is executed_

For ARCHER2 users these data are held under `/work/n01/shared/{{cookiecutter.project_slug}}` and `/work/n01/shared/nemo/FORCING` and are linked during the setup.

### Adding Additional NEMO Versions / Branches:

To fetch an additional NEMO version or feature branch after initial setup:
```bash
python scripts/add_nemo_version.py <nemo_version_or_branch>
```
For example:
```bash
python scripts/add_nemo_version.py 800-implement-single-last-barotropic-mode
```
See [docs/ADDING_NEMO_VERSIONS.md](docs/ADDING_NEMO_VERSIONS.md) for full details and options.

