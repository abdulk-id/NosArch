import re
import subprocess


def get_gpu_vendor() -> str:
    try:
        lspci_output: str = subprocess.check_output(["lspci"], text=True)

        if bool(re.search(r"(VGA|3D|Display).+Intel", lspci_output, re.IGNORECASE)):
            return "intel"

        if bool(re.search(r"(VGA|3D|Display).+(AMD|ATI)", lspci_output, re.IGNORECASE)):
            return "amd"

        lspci_nvidia_output: str = "\n".join(line for line in lspci_output.splitlines() if "nvidia" in line.lower())

        if bool(
            re.search(
                r"GTX 16[0-9]{2}|"
                + r"RTX [2-5][0-9]{3}|"
                + r"RTX PRO [0-9]{4}|"
                + r"Quadro RTX|"
                + r"RTX A[0-9]{4}|"
                + r"A[1-9][0-9]{2}|"
                + r"H[1-9][0-9]{2}|"
                + r"T4|"
                + r"L[0-9]+",
                lspci_nvidia_output,
                re.IGNORECASE,
            )
        ):
            return "nvidia_gsp"
        elif bool(
            re.search(
                r"GTX (9[0-9]{2}|10[0-9]{2})|"
                + r"GT 10[0-9]{2}|"
                + r"Quadro [PM][0-9]{3,4}|"
                + r"Quadro GV100|"
                + r"MX *[0-9]+|"
                + r"Titan (X|Xp|V)|"
                + r"Tesla V100",
                lspci_nvidia_output,
                re.IGNORECASE,
            )
        ):
            return "nvidia_non_gsp"

        return ""
    except subprocess.CalledProcessError:
        print("Failed to get GPU vendor")
        return ""


def is_gpu_intel() -> bool:
    return get_gpu_vendor() == "intel"


def is_gpu_amd() -> bool:
    return get_gpu_vendor() == "amd"


def is_gpu_nvidia_gsp() -> bool:
    return get_gpu_vendor() == "nvidia_gsp"


def is_gpu_nvidia_non_gsp() -> bool:
    return get_gpu_vendor() == "nvidia_non_gsp"
