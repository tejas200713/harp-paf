APPROVED_WORKLOADS = {
    "cpp": {
        "2bdda51193ff2ed5540bc56c321231969f135cc87ebc969b96df0d040276e2bb": "SUM=500000500000",
        "38309a7c2e27558d9d6fe98f1d3e2fdc0951300eb33caba77d24cb5c84df89e4": "TASK2=143999433",
        "544aa53606113501a500ccbf54b61a2b3d1df67072f0625b334bcf8508e66e91": "TASK3=49950000",
        "e69c7f56779d3b00aa224c164504699a6a93759e71565115acc38d0d96b0bbb3": "TASK4=666667166",
    }
}


def get_expected_output(language, source_hash):
    return APPROVED_WORKLOADS.get(language, {}).get(source_hash)
