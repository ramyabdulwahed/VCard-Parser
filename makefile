CC = gcc
CFLAGS = -Wall -std=c11 -g
LDFLAGS= -L.
INC = include/
SRC = src/
TARGET = bin/libvcparser.so
OBJS = VCParser.o LinkedListAPI.o
TEST_EXE = test_program  # Name of the test executable

parser: $(TARGET)	

$(TARGET): $(OBJS)
	$(CC) -shared -o $(TARGET) $(OBJS)
VCParser.o: $(SRC)VCParser.c $(INC)VCParser.h $(INC)LinkedListAPI.h LinkedListAPI.o
	$(CC) $(CFLAGS) -I$(INC) -c -fpic $(SRC)VCParser.c
LinkedListAPI.o: $(SRC)LinkedListAPI.c $(INC)LinkedListAPI.h
	$(CC) $(CFLAGS) -I$(INC) -c -fpic $(SRC)LinkedListAPI.c

$(TEST_EXE): main.c $(TARGET)
	$(CC)  -o $(TEST_EXE) main.c -I$(INC) -Lbin/ -L. -lvcparser

# Run the test
run: $(TEST_EXE)
	LD_LIBRARY_PATH=bin ./$(TEST_EXE)

clean:
	rm -rf $(TARGET) *.o
 