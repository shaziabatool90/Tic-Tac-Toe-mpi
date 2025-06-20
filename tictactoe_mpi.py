from mpi4py import MPI
import tkinter as tk

# Setup MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

class SimpleGame:
    def __init__(self, root, am_i_x):
        self.root = root
        self.am_i_x = am_i_x  # Am I player X?
        self.current_player = 'X'  # X goes first
        self.board = [' '] * 9  # 3x3 board
        
        # Create buttons
        self.buttons = []
        for i in range(9):
            btn = tk.Button(root, text=' ', font=('Arial', 30), width=3, height=1,
                           command=lambda idx=i: self.make_move(idx))
            btn.grid(row=i//3, column=i%3)
            self.buttons.append(btn)
        
        # Status label
        self.label = tk.Label(root, text="X's turn" if am_i_x else "Waiting for X")
        self.label.grid(row=3, columnspan=3)
        
        # Start listening for opponent's moves
        self.root.after(100, self.check_for_moves)

    def make_move(self, position):
        # Only allow move if it's your turn and space is empty
        if self.board[position] == ' ' and (
            (self.am_i_x and self.current_player == 'X') or 
            (not self.am_i_x and self.current_player == 'O')):
            
            # Make the move
            symbol = 'X' if self.am_i_x else 'O'
            self.buttons[position]['text'] = symbol
            self.board[position] = symbol
            
            # Check if game is over
            if self.check_winner(symbol):
                self.label.config(text="You win!")
                comm.send(('win', position), dest=1 if rank == 2 else 2)
            elif self.is_board_full():
                self.label.config(text="Draw!")
                comm.send(('draw', position), dest=1 if rank == 2 else 2)
            else:
                # Send move to opponent
                comm.send(('move', position), dest=1 if rank == 2 else 2)
                self.current_player = 'O' if self.current_player == 'X' else 'X'
                self.label.config(text="Waiting...")

    def check_for_moves(self):
        # Check if opponent sent a move
        if comm.Iprobe(source=1 if rank == 2 else 2):
            msg, pos = comm.recv(source=1 if rank == 2 else 2)
            
            if msg == 'move':
                # Update board with opponent's move
                symbol = 'O' if self.am_i_x else 'X'
                self.buttons[pos]['text'] = symbol
                self.board[pos] = symbol
                self.current_player = 'O' if self.current_player == 'X' else 'X'
                self.label.config(text="Your turn!")
            elif msg == 'win':
                self.buttons[pos]['text'] = 'O' if self.am_i_x else 'X'
                self.label.config(text="You lose!")
            elif msg == 'draw':
                self.buttons[pos]['text'] = 'O' if self.am_i_x else 'X'
                self.label.config(text="Draw!")
        
        # Keep checking
        self.root.after(100, self.check_for_moves)

    def check_winner(self, symbol):
        # Check rows, columns and diagonals
        wins = [(0,1,2), (3,4,5), (6,7,8),  # rows
                (0,3,6), (1,4,7), (2,5,8),  # columns
                (0,4,8), (2,4,6)]           # diagonals
        return any(self.board[i]==self.board[j]==self.board[k]==symbol for i,j,k in wins)

    def is_board_full(self):
        return ' ' not in self.board

# Server (rank 0) just matches players
if rank == 0:
    print("Server running - waiting for 2 players...")
    player1 = comm.recv(source=1, tag=1)
    player2 = comm.recv(source=2, tag=1)
    comm.send(True, dest=1)  # Tell player 1 they are X
    comm.send(False, dest=2) # Tell player 2 they are O
    print("Game started between Player 1 (X) and Player 2 (O)")

# Players (rank 1 and 2)
elif rank in [1, 2]:
    # Tell server we're ready
    comm.send(rank, dest=0, tag=1)
    
    # Get whether we're X or O
    am_i_x = comm.recv(source=0)
    
    # Start the game
    root = tk.Tk()
    root.title(f"Player {rank} ({'X' if am_i_x else 'O'})")
    game = SimpleGame(root, am_i_x)
    root.mainloop()