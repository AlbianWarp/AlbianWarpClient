import cmd
from CaosEvolution import CI


class CaosShell(cmd.Cmd):
    intro = "Hello, Welcome to CAOS Shell.\n"
    prompt = "(caos)"
    file = None

    def default(self, arg):
        print(CI.ExecuteCaos(arg).Content)


if __name__ == "__main__":
    CaosShell().cmdloop()
