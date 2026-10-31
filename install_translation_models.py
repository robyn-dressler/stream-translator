from argostranslate import package

def main():
    print("Installing translation models...")

    # Retrieve lists of remote and local packages
    available = package.get_available_packages()
    installed = {
        (p.from_code, p.to_code): p
        for p in package.get_installed_packages()
    }

    # Update existing packages and install new ones
    for p in available:
        key = (p.from_code, p.to_code)
        if key in installed:
            existing_package = installed[key]
            existing_package.update()
        else:
            p.install()

    print("Installation complete!")

if __name__ == '__main__':
    main()