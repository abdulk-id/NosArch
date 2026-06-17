import re
import subprocess


def get_lib32_gpu_drivers() -> set[str]:
    try:
        packages: set[str] = set()
        lspci_output: str = subprocess.check_output(["lspci"], text=True)

        if bool(re.search(rf"(VGA|Display).+{'Intel'}", lspci_output, re.IGNORECASE)):
            packages.update({"lib32-mesa", "lib32-vulkan-intel"})

        if bool(re.search(rf"(VGA|Display).+{'AMD'}", lspci_output, re.IGNORECASE)):
            packages.update({"lib32-mesa", "lib32-vulkan-radeon"})

        lspci_nvidia_output: str = "\n".join(
            line for line in lspci_output.splitlines() if "nvidia" in line.lower()
        )

        if bool(
            re.search(
                r"GTX 16[0-9]{2}|"
                r"RTX [2-5][0-9]{3}|"
                r"RTX PRO [0-9]{4}|"
                r"Quadro RTX|"
                r"RTX A[0-9]{4}|"
                r"A[1-9][0-9]{2}|"
                r"H[1-9][0-9]{2}|"
                r"T4|"
                r"L[0-9]+",
                lspci_nvidia_output,
                re.IGNORECASE,
            )
        ):
            packages.add("lib32-nvidia-utils")
        elif bool(
            re.search(
                r"GTX (9[0-9]{2}|10[0-9]{2})|"
                r"GT 10[0-9]{2}|"
                r"Quadro [PM][0-9]{3,4}|"
                r"Quadro GV100|"
                r"MX *[0-9]+|"
                r"Titan (X|Xp|V)|"
                r"Tesla V100",
                lspci_nvidia_output,
                re.IGNORECASE,
            )
        ):
            packages.add("lib32-nvidia-580xx-utils")

        return packages
    except Exception:
        print("Exception occured trying to get lib32 gpu drivers")
        return set()


if __name__ == "__main__":
    print(get_lib32_gpu_drivers())
