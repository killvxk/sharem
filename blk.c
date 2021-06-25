#include <stdio.h>

//These are test cases for callpop
int main()
{
	// all of these include a call 0x7, an add eax, eax, and x instruction(s) commented above, then a pop ebx
	//They should jump to the instruction listed above, before executing a pop.
	// jmp 0x6
	char* jmp = "\xE8\x02\x00\x00\x00\x01\xC0\xE9\x02\x00\x00\x00\x5B";

	// ljmp FWORD PTR ds:0x6
	char* ljmp = "\xE8\x02\x00\x00\x00\x01\xC0\xFF\x2D\x06\x00\x00\x00\x59";

	//jo 0x6
	char* jo = "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x80\x02\x00\x00\x00\x5B";

	//jno 0x6
	char* jno = "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x81\x02\x00\x00\x00\x5B";

	//jsn 0x6
	char* jsn = "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x89\x02\x00\x00\x00\x59";

	//js
	char* js = "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x88\x02\x00\x00\x00\x5B";

	//je 0x6
	char* je =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x84\x02\x00\x00\x00\x5B";

	//jz 0x6
	char* jz =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x84\x02\x00\x00\x00\x5B";

	//jne 0x6
	char* jne =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x85\x02\x00\x00\x00\x5B";

	//jnz 0x6
	char* jnz =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x85\x02\x00\x00\x00\x5B";

	//jb 0x6
	char* jb =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x82\x02\x00\x00\x00\x5B";

	//jnae 
	//Is equivalent to above

	//jc
	//Is equivalent to above

	
	//jae 0x6
	char* jae =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x83\x02\x00\x00\x00\x5B";

	//jnb
	//Is equivalent to above

	//jnc 0x6
	//Is equivalent to above

	//jbe 0x6
	char* jbe =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x86\x02\x00\x00\x00\x5B";

	//jna 0x6
	//Is equivalent to above

	//ja 0x6
	char* ja = "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x87\x02\x00\x00\x00\x5B" ;

	//jl 0x6
	char* jl =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x8C\x02\x00\x00\x00\x5B";


	//jnben 0x6
	//Is equivalent to above

	//jnge 0x6
	//Is equivalent to above

	//jge 0x6
	char* jge =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x8D\x02\x00\x00\x00\x5B";

	//jnl 0x6
	//Is equivalent to above

	//jle 0x6
	char* jle =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x8E\x02\x00\x00\x00\x5B";

	//jng 0x6
	//Is equivalent to above

	//jg 0x6
	char* jg =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x8F\x02\x00\x00\x00\x5B";

	//jnle 0x6
	//Is equivalent to above

	//jp 0x6
	char* jp =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x8A\x02\x00\x00\x00\x5B";


	//jpe 0x6
	//Is equivalent to above

	//jnp 0x6
	char* jnp =  "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x8B\x02\x00\x00\x00\x5B";

	//jpo 0x6
	//Is equivalent to above

	//jczz 0x6
	// char* jczz =
	//todo  

	//jecxz 0x6
	// char* jecxz =  
	//todo  

	//int 0x6
	char* intl =  "\xE8\x02\x00\x00\x00\x01\xC0\xCD\x06\x5B";

	//retf 0x6
	char* retf =  "\xE8\x02\x00\x00\x00\x01\xC0\xCA\x06\x00\x5B";

	//retf
	char* retf2 = "\xE8\x02\x00\x00\x00\x01\xC0\xCB\x5B";

	//db 0x6
	// char* db =
	//todo  

	//hlt
	char* hlt =  "\xE8\x02\x00\x00\x00\x01\xC0\xF4\x5B";

	//loop 0x6
	//char* loop =  
	//todo

	//ret 0x6
	char* ret =  "\xE8\x02\x00\x00\x00\x01\xC0\xC2\x06\x00\x5B";

	//ret
	char* ret2 = "\xE8\x02\x00\x00\x00\x01\xC0\xC3\x5B";


	//leave
	char* leave =  "\xE8\x02\x00\x00\x00\x01\xC0\xC9\x5B";

	//int3
	char* int3 =  "\xE8\x02\x00\x00\x00\x01\xC0\xCC\x5B";

	//insd 0x6, but the instruction won't go in, so...
	//ins    DWORD PTR es:[edi],dx
	char* insd =  "\xE8\x02\x00\x00\x00\x01\xC0\x6D\x5B";

	//enter 0x6,0x6
	char* enter =  "\xE8\x02\x00\x00\x00\x01\xC0\xC8\x06\x00\x06\x5B";

	//jns 0x6
	char* jns = "\xE8\x02\x00\x00\x00\x01\xC0\x0F\x89\x02\x00\x00\x00\x5B";




	//These ones should match
	//call 0x5
	//pop eax
	//pop eax
	char* str = "\xE8\x00\x00\x00\x00\x58\x58";



	//This one is a bad callpop
	// call a
	//pop ebx
	//(add eax,eax) x7 
	char* str2 = "\xE8\x05\x00\x00\x00\x5B\x01\xC0\x01\xC0\x01\xC0\x01\xC0\x01\xC0\x01\xC0\x01\xC0";




	printf("hello world");
}

//These are test cases for fnstenv, see fstenv_corpus for variations on this function to test other fstenv variations.
int fnstenv(){

	char* EAX = "\xD8\x30\x01\xC0\xD9\x30";
	char* EBX = "\xD8\x30\x01\xC0\xD9\x33";
	char* ECX = "\xD8\x30\x01\xC0\xD9\x31";
	char* EDX = "\xD8\x30\x01\xC0\xD9\x32";
	char* EDI = "\xD8\x30\x01\xC0\xD9\x37";
	char* ESI = "\xD8\x30\x01\xC0\xD9\x36";
	char* EBP = "\xD8\x30\x01\xC0\xD9\x75\x00";
	char* ESP = "\xD8\x30\x01\xC0\xD9\x34\x24\x00";
	char* EAX_PTR = "\xD8\x30\x01\xC0\xD9\xB0\x05\x00\x00\x00";
	char* EBX_PTR = "\xD8\x30\x01\xC0\xD9\xB3\x05\x00\x00\x00";
	char* ECX_PTR = "\xD8\x30\x01\xC0\xD9\xB1\x05\x00\x00\x00";
	char* EDX_PTR = "\xD8\x30\x01\xC0\xD9\xB2\x05\x00\x00\x00";
	char* EDI_PTR = "\xD8\x30\x01\xC0\xD9\xB7\x05\x00\x00\x00";
	char* ESI_PTR = "\xD8\x30\x01\xC0\xD9\xB6\x05\x00\x00\x00";
	char* EBP_PTR = "\xD8\x30\x01\xC0\xD9\xB5\x05\x00\x00\x00";
	char* ESP_PTR = "\xD8\x30\x01\xC0\xD9\xB4\x24\x05\x00\x00\x00";
	char* EAX_OFFSET_NUM = "\xD8\x30\x01\xC0\xD9\x70\x05\x00\x00";
	char* EBX_OFFSET_NUM = "\xD8\x30\x01\xC0\xD9\x73\x05\x00\x00";
	char* ECX_OFFSET_NUM = "\xD8\x30\x01\xC0\xD9\x71\x05\x00\x00";
	char* EDX_OFFSET_NUM = "\xD8\x30\x01\xC0\xD9\x72\x05\x00\x00";
	char* EDI_OFFSET_NUM = "\xD8\x30\x01\xC0\xD9\x77\x05\x00\x00";
	char* ESI_OFFSET_NUM = "\xD8\x30\x01\xC0\xD9\x76\x05\x00\x00";
	char* EBP_OFFSET_NUM = "\xD8\x30\x01\xC0\xD9\x75\x05\x00\x00";
	char* ESP_OFFSET_NUM = "\xD8\x30\x01\xC0\xD9\x74\x24\x05\x00\x00";
	char* R8 = "\x67\xD8\x30\x01\xC0\x41\xd9\x30";
	char* R9 = "\x67\xD8\x30\x01\xC0\x41\xd9\x31";
	char* R10 = "\x67\xD8\x30\x01\xC0\x41\xd9\x32";
	char* R11 = "\x67\xD8\x30\x01\xC0\x41\xd9\x33";
	char* R12 = "\x67\xD8\x30\x01\xC0\x41\xd9\x34\x24";
	char* R13 = "\x67\xD8\x30\x01\xC0\x41\xd9\x75\x00";
	char* R14 = "\x67\xD8\x30\x01\xC0\x41\xd9\x36";
	char* R15 = "\x67\xD8\x30\x01\xC0\x41\xd9\x37";
	char* R8_PTR =  "\x67\xD8\x30\x01\xC0\x41\xd9\xB0\x05\x00\x00\x00";
	char* R9_PTR =  "\x67\xD8\x30\x01\xC0\x41\xd9\xB1\x05\x00\x00\x00";
	char* R10_PTR = "\x67\xD8\x30\x01\xC0\x41\xd9\xB2\x05\x00\x00\x00";
	char* R11_PTR = "\x67\xD8\x30\x01\xC0\x41\xd9\xB3\x05\x00\x00\x00";
	char* R12_PTR = "\x67\xD8\x30\x01\xC0\x41\xd9\xB4\x24\x00\x00\x00";
	char* R13_PTR = "\x67\xD8\x30\x01\xC0\x41\xd9\xB5\x05\x00\x00\x00";
	char* R14_PTR = "\x67\xD8\x30\x01\xC0\x41\xd9\xB6\x05\x00\x00\x00";
	char* R15_PTR = "\x67\xD8\x30\x01\xC0\x41\xd9\xB7\x05\x00\x00\x00";
	char* R8_OFFSET_NUM =  "\x67\xD8\x30\x01\xC0\x41\xd9\x70\x05\x00\x00";
	char* R9_OFFSET_NUM =  "\x67\xD8\x30\x01\xC0\x41\xd9\x71\x05\x00\x00";
	char* R10_OFFSET_NUM = "\x67\xD8\x30\x01\xC0\x41\xd9\x72\x05\x00\x00";
	char* R11_OFFSET_NUM = "\x67\xD8\x30\x01\xC0\x41\xd9\x73\x05\x00\x00";
	char* R12_OFFSET_NUM = "\x67\xD8\x30\x01\xC0\x41\xd9\x74\x24\x05\x00\x00";
	char* R13_OFFSET_NUM = "\x67\xD8\x30\x01\xC0\x41\xd9\x75\x05\x00\x00";
	char* R14_OFFSET_NUM = "\x67\xD8\x30\x01\xC0\x41\xd9\x76\x05\x00\x00";
	char* R15_OFFSET_NUM = "\x67\xD8\x30\x01\xC0\x41\xd9\x77\x05\x00\x00";	

	__asm
	{
		add eax,eax
	}

	return 0;
}

int pushret()
{

	char* prEAX = "\x50\xC3";
	char* prEBX = "\x53\xC3";
	char* prECX = "\x51\xC3";
	char* prEDX = "\x52\xC3";
	char* prEDI = "\x57\xC3";
	char* prESI = "\x56\xC3";
	char* prEBP = "\x55\xC3";
	char* prESP = "\x54\xC3";
	char* prEAX_PAD = "\x50\xC2\x00\x00";
	char* prEBX_PAD = "\x53\xC2\x00\x00";
	char* prECX_PAD = "\x51\xC2\x00\x00";
	char* prEDX_PAD = "\x52\xC2\x00\x00";
	char* prEDI_PAD = "\x57\xC2\x00\x00";
	char* prESI_PAD = "\x56\xC2\x00\x00";
	char* prEBP_PAD = "\x55\xC2\x00\x00";
	char* prESP_PAD = "\x54\xC2\x00\x00";
	char* prEAX_RETF = "\x50\xCB";
	char* prEBX_RETF = "\x53\xCB";
	char* prECX_RETF = "\x51\xCB";
	char* prEDX_RETF = "\x52\xCB";
	char* prEDI_RETF = "\x57\xCB";
	char* prESI_RETF = "\x56\xCB";
	char* prEBP_RETF = "\x55\xCB";
	char* prESP_RETF = "\x54\xCB";
	char* prEAX_RETF_PAD = "\x50\xCA\x00\x00";
	char* prEBX_RETF_PAD = "\x53\xCA\x00\x00";
	char* prECX_RETF_PAD = "\x51\xCA\x00\x00";
	char* prEDX_RETF_PAD = "\x52\xCA\x00\x00";
	char* prEDI_RETF_PAD = "\x57\xCA\x00\x00";
	char* prESI_RETF_PAD = "\x56\xCA\x00\x00";
	char* prEBP_RETF_PAD = "\x55\xCA\x00\x00";
	char* prESP_RETF_PAD = "\x54\xCA\x00\x00";
	char* prR8 = "\x41\x50\xC3";
	char* prR9 = "\x41\x51\xC3";
	char* prR10 = "\x41\x52\xC3";
	char* prR11 = "\x41\x53\xC3";
	char* prR12 = "\x41\x54\xC3";
	char* prR13 = "\x41\x55\xC3";
	char* prR14 = "\x41\x56\xC3";
	char* prR15 = "\x41\x57\xC3";
	char* prR8_PAD = "\x41\x50\xC2\x05\x00";
	char* prR9_PAD = "\x41\x51\xC2\x05\x00";
	char* prR10_PAD = "\x41\x52\xC2\x05\x00";
	char* prR11_PAD = "\x41\x53\xC2\x05\x00";
	char* prR12_PAD = "\x41\x54\xC2\x05\x00";
	char* prR13_PAD = "\x41\x55\xC2\x05\x00";
	char* prR14_PAD = "\x41\x56\xC2\x05\x00";
	char* prR15_PAD = "\x41\x57\xC2\x05\x00";
	char* prR8_RETF = "\x41\x50\xCB";
	char* prR9_RETF = "\x41\x51\xCB";
	char* prR10_RETF = "\x41\x52\xCB";
	char* prR11_RETF = "\x41\x53\xCB";
	char* prR12_RETF = "\x41\x54\xCB";
	char* prR13_RETF = "\x41\x55\xCB";
	char* prR14_RETF = "\x41\x56\xCB";
	char* prR15_RETF = "\x41\x57\xCB";
	char* prR8_RETF_PAD = "\x41\x50\xCA\x05\x00";
	char* prR9_RETF_PAD = "\x41\x51\xCA\x05\x00";
	char* prR10_RETF_PAD = "\x41\x52\xCA\x05\x00";
	char* prR11_RETF_PAD = "\x41\x53\xCA\x05\x00";
	char* prR12_RETF_PAD = "\x41\x54\xCA\x05\x00";
	char* prR13_RETF_PAD = "\x41\x55\xCA\x05\x00";
	char* prR14_RETF_PAD = "\x41\x56\xCA\x05\x00";
	char* prR15_RETF_PAD = "\x41\x57\xCA\x05\x00";


	return 13;
}

int callpop()
{
	char* test = "\xE8\x01\x00\x00\x00\x5B\xE8\x02\x00\x00\x00\x58\x50\x50\x50\x50\x50\x50\x50\xC3\xC3\xC3\xC3\xC3\xE8\x00\x00\x00\x00\x5B";
	return 13;
}

